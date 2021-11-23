import ctypes
import threading
import time
import numpy as np


class WLM():
    trigger_on = False
    class TriggerThread(threading.Thread):
        
        def __init__(self, wlm, signal_channel=1, trigger_channel=4, moving_average_window = 10 ,*args, **kwargs):
            super(wlm.TriggerThread, self).__init__(*args, **kwargs)
            self.wlm = wlm
            self.scan_range = []
            self.signal_channel = signal_channel
            self.trigger_channel = trigger_channel
            self.moving_average_window = moving_average_window
            self._stop_event = threading.Event()

        def stop(self):
            self._stop_event.set()

        def stopped(self):
            return self._stop_event.isSet()

        def run(self):
            dev = np.array([0, 0])
            diffs = np.array([0, 0])
            mov_av = np.array([0, 0])
            # course = self.get_reference_course()

            while True:
                if self.stopped():
                    return
                if self.wlm.reference_course_amplitude is None:
                    pass
                else:
                    cur_lam = self.wlm.get_wavelength(channel=1)
                    
                    diff = cur_lam - self.wlm.reference_course_center
                    if (diff > 0):
                        self.wlm.set_deviation_signal(2000, channel=self.trigger_channel)
                    else:
                        self.wlm.set_deviation_signal(0, channel=self.trigger_channel)

    def __init__(self):
        self.dll = ctypes.windll.LoadLibrary('wlmData.dll')
        self.reference_course_center = None
        self.reference_course_amplitude = None
        self.trigger_thread = self.TriggerThread(self)
        self.start_trigger()

    def start_measurements(self):
        cCtrlStartMeasurment = ctypes.c_uint16(0x1002)
        self.dll.Operation(cCtrlStartMeasurment)
    
    def stop_measurements(self):
        cCtrlStop = ctypes.c_uint16(0x00)
        self.dll.Operation(cCtrlStop)
    
    def get_wavelength(self, channel = 1, units='air') -> float:
        self.dll.GetWavelengthNum.restype = ctypes.c_double
        self.dll.GetWavelengthNum.argtypes = [ctypes.c_long, ctypes.c_double]
        wavelength = self.dll.GetWavelengthNum(channel, 0)
        wavelength = self.convert_wavelength(wavelength, 'vac', units)
        return wavelength


    def get_reference_course(self, channel = 1) -> str:
        """
        Arguments: channel
        Returns: the string corresponing to the reference set on the WLM.
        For example, constant reference: '619.1234'
        Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
        """
        string_buffer = ctypes.create_string_buffer(1024)
        xp = ctypes.cast(string_buffer, ctypes.POINTER(ctypes.c_char))
        self.dll.GetPIDCourseNum.restype = ctypes.c_long
        self.dll.GetPIDCourseNum.argtypes = [ctypes.c_long, xp]
        self.dll.GetPIDCourseNum(channel, string_buffer)
        return string_buffer.value

    def set_reference_course(self,function:str, channel = 1):
        """
        Arguments: the string corresponing to the reference set on the WLM.
        For example, constant reference: '619.1234'
        Or a sawtooth with a center at '619.1234 + 0.001 * sawtooth(t/10)'
        Returns: None
        """ 
        if '+' and '*' in function:
            if function.index('+') < function.index('*'):
                center_wavelength,  scan_params= function.split('+', 1)
                scan_amplitude, scan_function = scan_params.split('*', 1)
                self.reference_course_center = float(center_wavelength)
                self.reference_course_amplitude = float(scan_amplitude)
            else:
                raise Exception("Center wavelength should go before scan parameters.\nPlease, comply to the format: c_lambda + amplitude * func (t / scan_speed)")
        else:
            self.reference_course_center = float(function)
            self.reference_course_amplitude = None
        if self.reference_course_center < 0:
            raise Exception("No signal at the wavelengthmeter!")
        else:
            string_buffer = ctypes.create_string_buffer(1024)
            xp = ctypes.cast(string_buffer, ctypes.POINTER(ctypes.c_char))
            self.dll.SetPIDCourseNum.restype = ctypes.c_long
            self.dll.SetPIDCourseNum.argtypes = [ctypes.c_long, xp]
            string_buffer.value = "{}".format(function).encode()
            self.dll.SetPIDCourseNum(channel, string_buffer)
        #!TODO split function into center_wavelength , scanning function.!
        
            
        
    def convert_wavelength(self, wavelength, from_, to_):
        """
        Arguments: wavelength - > current measured wavelength
        from_ - > the units of the 'wavelength' ('air', 'vac', 'THz')
        to_ : ('air', 'vac', 'THz')

        Returns: 'wavelength' in units 'to_'
        """
        cReturnTHz           = ctypes.c_long(0x0002)
        cReturnWavelangthAir = ctypes.c_long(0x0001)
        cReturnWavelangthVac = ctypes.c_long(0x0000)
        units = {'air': cReturnWavelangthAir, 'vac':cReturnWavelangthVac, 'THz':cReturnTHz}
        self.dll.ConvertUnit.restype = ctypes.c_double
        self.dll.ConvertUnit.argtypes = [ctypes.c_double, ctypes.c_long, ctypes.c_long]
        return self.dll.ConvertUnit(wavelength, units[from_], units[to_])

    def get_regulation_mode(self):
        self.dll.GetDeviationMode.restype = ctypes.c_bool
        self.dll.GetDeviationMode.argtypes = [ctypes.c_bool]
        return self.dll.GetDeviationMode(False)
    
    def set_regulation_mode(self, mode = False):
        self.dll.SetDeviationMode.restype = ctypes.c_long
        self.dll.SetDeviationMode.argtypes = [ctypes.c_bool]
        return self.dll.SetDeviationMode(mode)

    def get_deviation_sensitivity(self):
        # long GetDeviationSensitivity(long DS)
        self.dll.GetDeviationSensitivity.argtypes = [ ctypes.c_long ]
        self.dll.GetDeviationSensitivity.restype = ctypes.c_long
        return self.dll.GetDeviationSensitivity(0)
    def set_deviation_sensitivity(self, sensitivity):
        # long SetDeviationSensitivity(long DS)
        self.dll.SetDeviationSensitivity.argtypes = [ ctypes.c_long ]
        self.dll.SetDeviationSensitivity.restype = ctypes.c_long
        return self.dll.SetDeviationSensitivity(sensitivity)
    
    def get_deviation_signal(self, channel=4):
        # double GetDeviationSignalNum(long Port, double DS)
        self.dll.GetDeviationSignalNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
        self.dll.GetDeviationSignalNum.restype = ctypes.c_double
        return self.dll.GetDeviationSignalNum(channel, 0)
    def set_deviation_signal(self, deviation, channel=4):
        # long SetDeviationSignalNum(long Port, double DS)
        self.dll.SetDeviationSignalNum.argtypes = [ ctypes.c_long, ctypes.c_double ]
        self.dll.SetDeviationSignalNum.restype = ctypes.c_long
        return self.dll.SetDeviationSignalNum(channel, deviation)

    def start_trigger(self, signal_channel=1, trigger_channel=4):
        if self.trigger_on:
            self.stop_trigger()
        else:
            self.trigger_thread.start()
    def stop_trigger(self):
        self.trigger_thread.stop()
        self.trigger_thread.join()
        self.trigger_thread = self.TriggerThread(self)
