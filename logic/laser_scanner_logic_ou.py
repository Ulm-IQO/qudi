# -*- coding: utf-8 -*-
"""
This file contains a Qudi logic module for controlling scans of the
fourth analog output channel.  It was originally written for
scanning laser frequency, but it can be used to control any parameter
in the experiment that is voltage controlled.  The hardware
range is typically -10 to +10 V.

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

from collections import OrderedDict
import datetime
import matplotlib.pyplot as plt
import numpy as np
import time
from scipy.ndimage.filters import gaussian_filter
from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
#import PyDAQmx as daq


class LaserScannerLogic(GenericLogic):

    """This logic module controls scans of DC voltage on the fourth analog
    output channel of the NI Card.  It collects countrate as a function of voltage.
    """

    sig_data_updated = QtCore.Signal()

    # declare connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    do=Connector(interface='TriggerInterface')
    wavemeter1 = Connector(interface='WavemeterInterface')
    savelogic = Connector(interface='SaveLogic')
    #laser = Connector(interface = 'NewfocusLaserInterface')
    scan_range = StatusVar('scan_range', [-3, 3])
    number_of_repeats = StatusVar(default=100)
    resolution = StatusVar('resolution', 500)
    _scan_speed = StatusVar('scan_speed', 0.5)
    _static_v = StatusVar('goto_voltage', 0)
    _clock_frequency=StatusVar('clock_frequency', 50)
    _do_width=StatusVar('do_length', 10*10**-3)

    # parameters for pid loop to hold frequency
    pid_kp = StatusVar(default=-10)
    pid_ki = StatusVar(default=-0.00116)
    pid_setpoint = StatusVar(default=0)
    pid_timestep = StatusVar(default=300)
    frequency_history_length = 300

    sigChangeVoltage = QtCore.Signal(float)
    sigVoltageChanged = QtCore.Signal(float)
    sigScanNextLine = QtCore.Signal()
    sigUpdatePlots = QtCore.Signal()
    sigScanFinished = QtCore.Signal()
    sigScanStarted = QtCore.Signal()

    def __init__(self, **kwargs):
        """ Create VoltageScanningLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()
        self.stopRequested = False

        self.fit_x = []
        self.fit_y = []
        self.plot_x = []
        self.plot_y = []
        self.plot_y2 = []

        # array to store trace of frequencies to judge noise of laser locking
        # first element ist most recent and last element is oldest frequency
        self.freq_history = np.zeros(self.frequency_history_length)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._scanning_device = self.confocalscanner1()
        self._wavemeter_device = self.wavemeter1()
        self._save_logic = self.savelogic()
        #self._laser_device = self.laser()
        self._do=self.do()

        # start acquisition of wavemeter so that current wavelength/frequency is always available
        # during execution of laser scanner logic
        self._wavemeter_device.start_acqusition()

        # Reads in the maximal scanning range. The unit of that scan range is
        # micrometer!
        self.a_range = self._scanning_device.get_position_range()[3]

        # Initialise the current position of all four scanner channels.
        self.current_position = self._scanning_device.get_scanner_position()

        # initialise the range for scanning
        self.set_scan_range(self.scan_range)

        # Keep track of the current static voltage even while a scan may cause the real-time
        # voltage to change.

        self.goto_voltage(self._static_v)
        self._re_pump='off'
        # setup timer for pid refresh
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.pid_timestep)

        # Sets connections between signals and functions
        self.sigChangeVoltage.connect(self._change_voltage, QtCore.Qt.QueuedConnection)
        self.sigScanNextLine.connect(self._do_next_line, QtCore.Qt.QueuedConnection)

        self.timer.timeout.connect(self._calcNextPIDStep, QtCore.Qt.QueuedConnection)

        # Initialization of internal counter for scanning
        self._scan_counter_up = 0
        self._scan_counter_down = 0
        # Keep track of scan direction
        self.upwards_scan = True

        self.pid_enable = False

        # calculated number of points in a scan, depends on speed and max step size
        self._num_of_steps = 50  # initialising.  This is calculated for a given ramp.

        self.timer.start(self.pid_timestep)

        #############################

        # TODO: allow configuration with respect to measurement duration
        self.acquire_time = 20  # seconds

        # default values for clock frequency and slowness
        # slowness: steps during retrace line
        self.set_resolution(self.resolution)
        self._goto_speed = 0.5  # 0.01  # volt / second
        self.set_scan_speed(self._scan_speed)
        self._smoothing_steps = 3  # steps to accelerate between 0 and scan_speed
        self._max_step = 0.01  # volt
        self._clock_frequency = max(50,int(self._scan_speed*50))
        ##############################

        # Initialie data matrix
        self._initialise_data_matrix(100)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._wavemeter_device.stop_acqusition()
        self.stopRequested = True

    def get_pid_gains(self):
        """ Returns proportional (kp) and integral (ki) gain of pid controller for holding laser frequency.
            @return list(float): (kp, ki)
        """
        result = [self.pid_kp, self.pid_ki]
        return result

    def set_pid_gains(self, kp, ki):
        """ Sets proportional and integral gain of pid controller for holding laser frequency.
            @param float kp: proportional gain
            @param float ki: integral gain

            @return array: new (kp, ki)
        """
        self.pid_kp = kp
        self.pid_ki = ki
        result = [self.pid_kp, self.pid_ki]
        return result

    def set_frequency_history_legnth(self, length):
        """ Sets length of array that stores frequency trace during pid loop.
            @param int length: array length

            @return int: frequency_history_length
        """
        self.frequency_history_length = length
        return self.frequency_history_length

    def restart_frequency_recording(self):
        """ Re-initializes array freq_history that tracks frequency trace during PID loop

            @return int: 0:OK
        """
        self.freq_history = np.zeros(self.frequency_history_length)
        return 0

    def start_frequency_holding(self, frequency=None, pid_update_time=None):
        """ This function enables drives the laser piezo such that it stays on desired frequency
            if given frequency is further away from current frequency than 50MHz a coarse approach
            is done where the piezo voltage is ramped proportional to the frequency delta
            afterwards the PI loop  is activated for keeping the desired frequency of the laser

            @param float frequency: frequency (THz) that laser should stay at.
                                    If not given, current frequency will be used instead
            @param float pid_update_time: time in ms after which pid loop is updated
                                          default is 300ms

            @return float: PID setpoint
        """

        if pid_update_time is not None:
            self.pid_timestep = pid_update_time
        if frequency is None:
            self.pid_setpoint = self._wavemeter_device.get_current_frequency()
        else:
            self.pid_setpoint = frequency

        # do coarse approach to frequency if it is to far away
        self.goto_voltage(0.5)
        #self.log.info('delta:'+str(self.pid_setpoint)+'-'+str(self._wavemeter_device.get_current_frequency()))
        if abs(self.pid_setpoint-self._wavemeter_device.get_current_frequency())*1000 > 10:
            #self.log.info('goto_freq first')
            self.set_scan_speed(0.5)
            self._re_pump='off'
            self.goto_frequency(self.pid_setpoint, 0.05, 10)
        self.set_scan_speed(0.1)
        # start PID loop
        # reset integral counter of pid loop
        self.pid_integrated = 0

        # reset frequency history trace
        self.freq_history = np.zeros(self.frequency_history_length)

        # enable pid loop
        self.pid_enable = True

        return self.pid_setpoint

    def stop_frequency_holding(self):
        """ This function disables the PI loop that keeps the current frequency of the laser
        """
        self.pid_enable = False

    def _calcNextPIDStep(self):
        """ This function implements PI loop to keep the current frequency of the laser
        """
        self.pid_pv = self._wavemeter_device.get_current_frequency()

        if self.pid_enable and self.module_state() == 'idle':
            # save current frequency value into first position of freq_history array
            # and shift the others back
            self.freq_history = np.roll(self.freq_history, 1)
            self.freq_history[0] = self.pid_pv

            delta = self.pid_setpoint - self.pid_pv
            self.log.debug('freq delta='+str(delta*1000)+'GHz')
            self.pid_integrated += delta
            # Calculate PID controller:
            self.pid_P = self.pid_kp * delta
            self.pid_I = self.pid_ki * self.pid_timestep * self.pid_integrated

            voltage_change = (self.pid_P + self.pid_I)/5.8
            #self.log.info('voltage_change='+str(voltage_change)+'V')
            if abs(voltage_change)> 4*10**-7:
                voltage = self.get_current_voltage() + voltage_change

                self.set_scan_speed(max(voltage_change,0.01))
                #self.log.debug('voltage to apply to scanner:'+str(voltage)+'V')
                if voltage <1 and voltage >0:
                    self.goto_voltage(voltage)
                else:
                    self.log.info('out of range')
            else:
                pass

            # directly change voltage on NIDAQ card, as voltage steps of pid should be small
            #if self.a_range[0] <= voltage <= self.a_range[1]:
            #    self._static_v = voltage
            #    self._scanning_device.scanner_set_position(a=voltage)
                # self.log.debug('voltage set!')
            #else:
             #   self.log.error('Cannot keep frequency as piezo voltage out of range.')

        self.timer.start(self.pid_timestep)

    def goto_frequency(self, frequency, freq_accuracy = 0.01, max_steps = 100):
        """Tries to iteratively adjust piezo voltage such that frequency measured by wavementer is
        withing frequency +-freq_accuracy range.

        @param float frequency: desired laser frequency (THz)
        @param float freq_accuracy: desired accuracy for frequency approach (GHz)
        @param int max_steps: maximum number of iteration steps to reach desired frequency

        @return int: error code (0:OK, -1:error)
        """
        # calculate maximum voltage range on a-axis that corresponds to
        # full frequency range of piezo
        range_a = self.a_range[1]-self.a_range[0]

        general_timer=time.time()
        wavelength = round(2.997965*10**8/(frequency*10**3*1.00029), 2)
        self.log.info('centering piezo')
        self._laser_device.set_piezo_percentage(50)
        self.goto_voltage(0)
        self._laser_device.set_wavelength(wavelength)
        self.log.info('coarse approaching')
        t = abs(wavelength-self._laser_device.get_wavelength())/0.1+2
        time.sleep(t*2)
        timer = 0
        while abs(self._laser_device.get_wavelength()-wavelength)>0.1:
            time.sleep(0.5)
            timer+=1
            if timer >=100:
                self.log.info('time out while coarse approaching' )
                timer = 1000
                break
        if timer >= 800:
            return False

        self._laser_device.Query('SOUR:WAVE:SLEW:FORW 0.05')
        self._laser_device.Query('SOUR:WAVE:SLEW:RET 0.05')

        timer = 0
        while self._wavemeter_device.get_current_frequency() < 0:
            time.sleep(0.1)
        current_wavelength = round(2.997965*10**8/(self._wavemeter_device.get_current_frequency()*10**3*1.00029),3)
        self.log.info(str(wavelength) + ', ' + str(current_wavelength))
        self.log.info('difference: ' + str(wavelength - current_wavelength))
        while abs(wavelength-current_wavelength)>0.05:
            self._laser_device.set_wavelength(wavelength+(wavelength-current_wavelength))
            time.sleep(5)
            while self._wavemeter_device.get_current_frequency() < 0:
                time.sleep(0.1)
            if self._wavemeter_device.get_current_frequency() > 0:
                current_wavelength = 2.997965*10**8/(self._wavemeter_device.get_current_frequency()*10**3*1.00029)
                self.log.info('wavelenth1: '+ str(current_wavelength))
            timer+=1
            if timer >= 10:
                self.log.info('time out while coarse aligning with wavemeter')
                timer += 1000
                return False
        self.log.info(str(wavelength)+', '+str(current_wavelength))
        self.log.info('difference: ' + str(wavelength - current_wavelength))

        while self._wavemeter_device.get_current_frequency() < 0:
            time.sleep(0.1)
        current_freq = self._wavemeter_device.get_current_frequency()
        self.log.info('piezo approaching')
        steps = 0
        while abs(current_freq-frequency) > freq_accuracy/1000 and steps < max_steps and (time.time()-general_timer)<=100:
            #calculate change in piezo voltage to get to desired frequency
            #change frequency diff to GHz. Scanning range of piezo equals 115GHz from -2.9V to 2.9V
            delta_volt = (current_freq-frequency)*1000/116 * self.a_range[1]
            self.log.info('delta_freq:'+str(current_freq-frequency))
            self.log.info('delta_volt:'+str(delta_volt))
            new_set_volt = self.get_current_voltage() + delta_volt
             #check that calculated voltage is within Piezo voltage range
            if new_set_volt > (self.a_range[0]) and new_set_volt < (self.a_range[1]):
                #print('passed_new_voltage: '+str(new_set_volt))
                self.set_scan_speed(min(0.1,abs(delta_volt)))
                self.set_clock_frequency(20)
                #print('new_scan_speed:'+str(self._scan_speed))
                self.goto_voltage(new_set_volt)
                # wait until scanning finished, there should a better way to do it!
                #self.log.info(str(max(abs(delta_volt)/self._scan_speed*2,7)))
                timer_module=0
                while self._scanning_device.module_state() == 'locked' and timer_module<=100:
                    timer_module+=1
                    time.sleep(0.1)
                    # wait until scanning stopped
                if timer_module > 100:
                    self.log.exception('module timeout')
                    self.set_scan_speed(0.1)
                    return False
                while self._wavemeter_device.get_current_frequency() < 0:
                    time.sleep(0.1)
                current_freq = self._wavemeter_device.get_current_frequency()
            else:
                self.log.error('Cannot reach desired frequency as piezo voltage is out of range!')
                self.log.info(str(new_set_volt))
                self.set_scan_speed(0.1)
                return False
        if (time.time()-general_timer)>100:
            self.log.exception('general timeout')
            self.set_scan_speed(0.1)
            return False
        if steps == max_steps and (abs(current_freq-frequency) > freq_accuracy/1000):
            self.log.error('Could not reach desired frequency within max number of steps!')
            self.set_scan_speed(0.1)
            return False
        if steps <= max_steps and (abs(current_freq-frequency) < freq_accuracy/1000):
            self.log.info('desired frequency reached')
            self.set_scan_speed(0.1)
            return True
#
    @QtCore.Slot(float)
    def goto_voltage(self, volts=None):
        """Forwarding the desired output voltage to the scanning device.

        @param float volts: desired voltage (volts)

        @return int: error code (0:OK, -1:error)
        """
        # print(tag, x, y, z)
        # Changes the respective value
        if volts is not None:
            self._static_v = volts

        # Checks if the scanner is still running
        t=0
        while (self.module_state() == 'locked'
                or self._scanning_device.module_state() == 'locked') and t<300:
            time.sleep(0.1)
            t+1
            #self.log.info('Cannot goto, because scanner is locked!')
        if t >= 300:
            self.log.exception('scanner timeout')
            return False
        self.sigChangeVoltage.emit(volts)
        return 0

    def _change_voltage(self, new_voltage):
        """ Threaded method to change the hardware voltage for a goto.

        @return int: error code (0:OK, -1:error)
        """
        current_v = self.get_current_voltage()
        try:
            ramp_scan = self._generate_ramp(current_v, new_voltage, self._goto_speed)#abs(new_voltage-current_v)/3)
        except:
            ramp_scan = self._generate_ramp(current_v, new_voltage, abs(new_voltage-current_v)/3)
        self._initialise_scanner()
        ignored_counts = self._scan_line(ramp_scan)
        self._close_scanner()
        self.sigVoltageChanged.emit(new_voltage)
        return 0

    def _goto_during_scan(self, voltage=None):

        if voltage is None:
            return -1

        goto_ramp = self._generate_ramp(self.get_current_voltage(), voltage, self._goto_speed)
        ignored_counts = self._scan_line(goto_ramp)

        return 0

    def set_clock_frequency(self, clock_frequency):
        """Sets the frequency of the clock

        @param int clock_frequency: desired frequency of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = float(clock_frequency)
        # checks if scanner is still running
        if self.module_state() == 'locked':
            return -1
        else:
            return 0

    def set_resolution(self, resolution):
        """ Calculate clock rate from scan speed and desired number of pixels """
        self.resolution = resolution
        scan_range = abs(self.scan_range[1] - self.scan_range[0])
        duration = scan_range / self._scan_speed
        new_clock = resolution / duration
        return self.set_clock_frequency(new_clock)

    def set_scan_range(self, scan_range):
        """ Set the scan rnage """
        r_max = np.clip(scan_range[1], self.a_range[0], self.a_range[1])
        r_min = np.clip(scan_range[0], self.a_range[0], r_max)
        self.scan_range = [r_min, r_max]


    def set_voltage(self, volts):
        """ Set the channel idle voltage """
        self._static_v = np.clip(volts, self.a_range[0], self.a_range[1])
        self.goto_voltage(self._static_v)

    def set_scan_speed(self, scan_speed):
        """ Set scan speed in volt per second """
        self._scan_speed = np.clip(scan_speed, 1e-9, 1e6)
        self._goto_speed = self._scan_speed

    def set_scan_lines(self, scan_lines):
        self.number_of_repeats = int(np.clip(scan_lines, 1, 1e6))

    def _initialise_data_matrix(self, scan_length):
        """ Initializing the ODMR matrix plot. """

        self.scan_matrix = np.zeros((self.number_of_repeats, scan_length))
        self.scan_matrix2 = np.zeros((self.number_of_repeats, scan_length))
        self.plot_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length)
        self.plot_y = np.zeros(scan_length)
        self.plot_y2 = np.zeros(scan_length)
        self.fit_x = np.linspace(self.scan_range[0], self.scan_range[1], scan_length*10)
        self.fit_y = np.zeros(scan_length*10)

    def get_pid_rmse(self):
        """Calculates root mean square error of frequency holding done by PID loop
           using freq_history array of measured frequencies and set point of pid loop as target

        @return float: Root mean square error in MHz
        """
        # remove elements that are 0 as they do not contain a correct laser freq
        if 0 in self.freq_history:
            freq_measured = self.freq_history[self.freq_history != 0]
        else:
            freq_measured = self.freq_history
        return np.sqrt(((freq_measured - self.pid_setpoint) ** 2).mean())*10e6

    def get_current_voltage(self):
        """returns current voltage of hardware device(atm NIDAQ 4th output)"""
        return self._scanning_device.get_scanner_position()[3]

    def _initialise_scanner(self):
        """Initialise the clock and locks for a scan"""
        self.module_state.lock()
        self._scanning_device.module_state.lock()

        returnvalue = self._scanning_device.set_up_scanner_clock(
            clock_frequency=self._clock_frequency)
        if returnvalue < 0:
            self._scanning_device.module_state.unlock()
            self.module_state.unlock()
            self.set_position('scanner')
            return -1

        returnvalue = self._scanning_device.set_up_scanner()
        if returnvalue < 0:
            self._scanning_device.module_state.unlock()
            self.module_state.unlock()
            self.set_position('scanner')
            return -1

        return 0

    def start_scanning(self, v_min=None, v_max=None):
        """Setting up the scanner device and starts the scanning procedure

        @return int: error code (0:OK, -1:error)
        """

        self.current_position = self._scanning_device.get_scanner_position()
        print(self.current_position)

        if v_min is not None:
            self.scan_range[0] = v_min
        else:
            v_min = self.scan_range[0]
        if v_max is not None:
            self.scan_range[1] = v_max
        else:
            v_max = self.scan_range[1]

        self._scan_counter_up = 0
        self._scan_counter_down = 0
        self.upwards_scan = True

        # TODO: Generate Ramps
        self._upwards_ramp = self._generate_ramp(v_min, v_max, self._scan_speed)
        self._downwards_ramp = self._generate_ramp(v_max, v_min, self._scan_speed)

        self._initialise_data_matrix(len(self._upwards_ramp[3]))

        # Lock and set up scanner
        returnvalue = self._initialise_scanner()
        if returnvalue < 0:
            # TODO: error message
            return -1

        self.sigScanNextLine.emit()
        self.sigScanStarted.emit()
        return 0

    def stop_scanning(self):
        """Stops the scan

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
                #self._close_scanner()
        return 0

    def _close_scanner(self):
        """Close the scanner and unlock"""
        with self.threadlock:
            self.kill_scanner()
            self.stopRequested = False
            if self.module_state.can('unlock'):
                self.module_state.unlock()

    def _do_next_line(self):
        """ If stopRequested then finish the scan, otherwise perform next repeat of the scan line
        """
        # stops scanning
        if self.stopRequested or self._scan_counter_down >= self.number_of_repeats:
            print(self.current_position)
            self._goto_during_scan(self.scan_range[0])
            self._close_scanner()
            self._scanning_device.scanner_set_position(
                self._scanning_device.get_scanner_position()[0],
                self._scanning_device.get_scanner_position()[1],
                self._scanning_device.get_scanner_position()[2],
                self.get_current_voltage()
            )
            self.sigScanFinished.emit()
            return

        if self._scan_counter_up == 0:
            # move from current voltage to start of scan range.
            self._goto_during_scan(self.scan_range[0])

        if self.upwards_scan:
            counts = self._scan_line(self._upwards_ramp)
            self.scan_matrix[self._scan_counter_up] = counts
            self.plot_y += counts
            self.fit_y =gaussian_filter(np.interp(self.fit_x,self.plot_x,counts),sigma=20)
            self._scan_counter_up += 1
            self.upwards_scan = False
        else:
            counts = self._scan_line(self._downwards_ramp)
            self.scan_matrix2[self._scan_counter_down] = counts
            self.plot_y2 += counts
            self._scan_counter_down += 1
            self.upwards_scan = True

        self.sigUpdatePlots.emit()
        self.sigScanNextLine.emit()

    def _generate_ramp(self, voltage1, voltage2, speed):
        """Generate a ramp vrom voltage1 to voltage2 that
        satisfies the speed, step, smoothing_steps parameters.  Smoothing_steps=0 means that the
        ramp is just linear.

        @param float voltage1: voltage at start of ramp.

        @param float voltage2: voltage at end of ramp.
        """

        # It is much easier to calculate the smoothed ramp for just one direction (upwards),
        # and then to reverse it if a downwards ramp is required.

        v_min = min(voltage1, voltage2)
        v_max = max(voltage1, voltage2)

        if v_min == v_max:
            ramp = np.array([v_min, v_max])
        else:
            # These values help simplify some of the mathematical expressions
            linear_v_step = speed / self._clock_frequency
            smoothing_range = self._smoothing_steps + 1

            # Sanity check in case the range is too short

            # The voltage range covered while accelerating in the smoothing steps
            v_range_of_accel = sum(
                n * linear_v_step / smoothing_range for n in range(0, smoothing_range)
                )

            # Obtain voltage bounds for the linear part of the ramp
            v_min_linear = v_min + v_range_of_accel
            v_max_linear = v_max - v_range_of_accel
            #self.log.info('voltage_bounds:'+str(v_min_linear)+','+str(v_max_linear))
            #self.log.info(str(v_min_linear)+str(v_max_linear))
            if v_min_linear > v_max_linear:
                self.log.warning(
                    'Voltage ramp too short to apply the '
                    'configured smoothing_steps. A simple linear ramp '
                    'was created instead.')
                #self.log.info('voltage_bounds:' + str(v_min) + ',' + str(v_max))
                num_of_linear_steps = np.rint((v_max - v_min) / linear_v_step)
                while num_of_linear_steps <=4:
                    self.set_clock_frequency(2*self._clock_frequency)
                    linear_v_step = speed / self._clock_frequency
                    num_of_linear_steps = np.rint((v_max - v_min) / linear_v_step)
                    self.log.warning('increasing clock frequency to enable ramp')
                ramp = np.linspace(v_min, v_max, num_of_linear_steps)



            else:

                num_of_linear_steps = np.rint((v_max_linear - v_min_linear) / linear_v_step)

                # Calculate voltage step values for smooth acceleration part of ramp
                smooth_curve = np.array(
                    [sum(
                        n * linear_v_step / smoothing_range for n in range(1, N)
                        ) for N in range(1, smoothing_range)
                    ])

                accel_part = v_min + smooth_curve
                decel_part = v_max - smooth_curve[::-1]

                linear_part = np.linspace(v_min_linear, v_max_linear, num_of_linear_steps)

                ramp = np.hstack((accel_part, linear_part, decel_part))

        # Reverse if downwards ramp is required
        if voltage2 < voltage1:
            ramp = ramp[::-1]

        # Put the voltage ramp into a scan line for the hardware (4-dimension)
        spatial_pos = self._scanning_device.get_scanner_position()

        scan_line = np.vstack((
            np.ones((len(ramp), )) * spatial_pos[0],
            np.ones((len(ramp), )) * spatial_pos[1],
            np.ones((len(ramp), )) * spatial_pos[2],
            ramp
            ))
        #print(ramp)
        return scan_line

    def _scan_line(self, line_to_scan=None):
        """do a single voltage scan from voltage1 to voltage2

        """
        if line_to_scan is None:
            self.log.error('Voltage scanning logic needs a line to scan!')
            return -1
        try:
            # scan of a single line
            counts_on_scan_line = self._scanning_device.scan_line(line_to_scan)
            # self._scanning_device.scanner_set_position(
            #  self._scanning_device.get_scanner_position()[0],
            #    self._scanning_device.get_scanner_position()[1],
            #    self._scanning_device.get_scanner_position()[2],
            #    self.get_current_voltage()
            #)
            #self.log.debug(str(np.where(counts_on_scan_line==max(counts_on_scan_line))[0])) ##ToDo: change this line to a real peak finder
            if self._re_pump=='on' and self._do_width!=0:
                time.sleep(0.05)
                self._do.simple_on('/Dev1/Port0/Line5')
                time.sleep(self._do_width)
                self._do.simple_off('/Dev1/Port0/Line5')
            x0=np.random.randint(len(counts_on_scan_line.transpose()[0]))
            gamma=np.random.normal(5,1)
            a=np.random.normal(10,3)*np.pi*gamma/2
            x=np.arange(len(counts_on_scan_line.transpose()[0]))
            y=self.Lorentzien(x,x0,gamma,a)
            y_noise=np.random.poisson(y,y.shape)+np.random.poisson(1,y.shape)

            return y_noise#counts_on_scan_line.transpose()[0]

        except Exception as e:
            self.log.error('The scan went wrong, killing the scanner.')
            self.stop_scanning()
            self.sigScanNextLine.emit()
            raise e

    def kill_scanner(self):
        """Closing the scanner device.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self._scanning_device.close_scanner()
            self._scanning_device.close_scanner_clock()
        except Exception as e:
            self.log.exception('Could not even close the scanner, giving up.')
            raise e
        try:
            if self._scanning_device.module_state.can('unlock'):
                self._scanning_device.module_state.unlock()
        except:
            self.log.exception('Could not unlock scanning device.')
        return 0

    def save_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Save the counter trace data and writes it to a file.

        @return int: error code (0:OK, -1:error)
        """
        if tag is None:
            tag = ''

        self._saving_stop_time = time.time()

        filepath = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath2 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        filepath3 = self._save_logic.get_path_for_module(module_name='LaserScanning')
        timestamp = datetime.datetime.now()

        if len(tag) > 0:
            filelabel = tag + '_volt_data'
            filelabel2 = tag + '_volt_data_raw_trace'
            filelabel3 = tag + '_volt_data_raw_retrace'
        else:
            filelabel = 'volt_data'
            filelabel2 = 'volt_data_raw_trace'
            filelabel3 = 'volt_data_raw_retrace'

        # prepare the data in a dict or in an OrderedDict:
        data = OrderedDict()
        data['frequency (Hz)'] = self.plot_x
        data['trace count data (counts/s)'] = self.plot_y
        data['retrace count data (counts/s)'] = self.plot_y2

        data2 = OrderedDict()
        data2['count data (counts/s)'] = self.scan_matrix[:self._scan_counter_up, :]

        data3 = OrderedDict()
        data3['count data (counts/s)'] = self.scan_matrix2[:self._scan_counter_down, :]

        parameters = OrderedDict()
        parameters['Number of frequency sweeps (#)'] = self._scan_counter_up
        parameters['Start Voltage (V)'] = self.scan_range[0]
        parameters['Stop Voltage (V)'] = self.scan_range[1]
        parameters['Scan speed [V/s]'] = self._scan_speed
        parameters['Clock Frequency (Hz)'] = self._clock_frequency

        fig = self.draw_figure(
            self.scan_matrix,
            self.plot_x,
            self.plot_y,
            self.fit_x,
            self.fit_y,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        fig2 = self.draw_figure(
            self.scan_matrix2,
            self.plot_x,
            self.plot_y2,
            self.fit_x,
            self.fit_y,
            cbar_range=colorscale_range,
            percentile_range=percentile_range)

        self._save_logic.save_data(
            data,
            filepath=filepath,
            parameters=parameters,
            filelabel=filelabel,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp
        )

        self._save_logic.save_data(
            data2,
            filepath=filepath2,
            parameters=parameters,
            filelabel=filelabel2,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig
        )

        self._save_logic.save_data(
            data3,
            filepath=filepath3,
            parameters=parameters,
            filelabel=filelabel3,
            fmt='%.6e',
            delimiter='\t',
            timestamp=timestamp,
            plotfig=fig2
        )

        self.log.info('Laser Scan saved to:\n{0}'.format(filepath))
        return 0

    def draw_figure(self, matrix_data, freq_data, count_data, fit_freq_vals, fit_count_vals, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = np.array([np.min(matrix_data), np.max(matrix_data)])
        else:
            cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(
            matrix_data,
            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
            origin='lower',
            vmin=cbar_range[0],
            vmax=cbar_range[1],
            extent=[
                np.min(freq_data),
                np.max(freq_data),
                0,
                self.number_of_repeats
                ],
            aspect='auto',
            interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which='both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig

    def Lorentzien(self,x,x0,gamma,a):
        return a/np.pi*gamma/2/((x-x0)**2+(gamma/2)**2)

    def peakfind(self,x,y):
        pass
