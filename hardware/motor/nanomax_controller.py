import math
import numpy as np
from datetime import datetime as dt
from time import time, sleep
from random import random
from scipy.optimize import minimize

from .misc import dated_folder

# Measurement apparatus imports (LabInterface.trunk.labpy3)
from . import monochromator
from .powermeter import Powermeter
# from .picoharp import PicoHarp
from .detectorConnection import mysocket as detect_o_tron


# Thorlabs stepper motor and piezo actuators
from .thorlabs_mdt import PiezoController
import thorlabs_apt as apt
from conda_env.specs import detect


# Define the noise floor for the SNSPDs
SNSPD_DARK_COUNTS = 250

class StepperMotor(object): pass

class NanomaxController(object):
    '''
    This class controls the stepper motors in the X-Y plane and
    X-Y-Z plane for the piezo controllers for the Nanomax 600 stage.
    -----
    dependencies:
        (git - https://git-scm.com/download/)
        APT CONTROLLER BSC203 => (DRV001 Stepper motor)
        --------------
        pip install git+http://github.com/qpit/thorlabs_apt@master
        copy the file C:\Program Files\Thorlabs\APT\APT Server\APT.dll
        to C:\Windows\System32
        
        PIEZO CONTROLLER (MDT693A)
        -------------
        conda install pyserial
        
        OPTICAL MEASUREMENT
        -------------
        1. powermeter python object in LabInterface package
        2. detectorConnection python object in LabInterface for SNSPDs
        
        
    other requirements:
        Make sure that the APT/MST GUIs are closed whilst running this script
    '''
    # number of times to measure power meter
    NUM_INTEGRATIONS = 1
    UNITS = "dBm"
    
    def __init__(self, detector, measure_func, monochromator=None, input_power=0, logfile=True, wavelength_offset = 0.0):
        
        # Initialise the detector we use for optimising the position
        if type(detector) not in [Powermeter, detect_o_tron]:#, PicoHarp]:
            raise RuntimeError("%s detector has not been implemented yet" % detector)
        
        # Set our detector
        print ('Nanomax detector for optimising position is %s' % type(detector))
        self.detector = detector 
        self.measure = measure_func
        
        if type(detector) is Powermeter:
            print ('detector units: {}'.format(detector.unit))
            if detector.unit == 'dBm':
                self.noise_floor = -120.0
                self.UNITS = 'dBm'
            else:
                self.noise_floor = 0.0
                self.UNITS = 'W'
        else:
            self.noise_floor = SNSPD_DARK_COUNTS 
            self.UNITS = 'Hz'
        
        print ('The noise floor is {} {}'.format(self.noise_floor, self.UNITS))
        
        # Set up our monochromater if we are using one
        self.monochromator = monochromator
        
        # Set the monochromator to go to a wavelength offset if we require
        self.wavelength_offset = wavelength_offset #nm
        if monochromator is not None and wavelength_offset != 0.0:
            print ('Moving to a wavelength offset of {} nm'.format(wavelength_offset))
            self.monochromator.goto_wavelength(wavelength_offset)
       
        # Find the available stepper motor devices
        devices = apt.list_available_devices()
        
        # If devices found print them otherwise raise an error
        if devices:
            print ("Available devices:", devices)
        else:
            self.release()
            raise RuntimeError("Could not locate a Nanomax stepper motor controller")
        
        ####### Stepper motor serial numbers ##########
        # X axis controller has S/N 90870(105) ==> Slot 1
        # Y axis controller has S/N 90870(106) ==> Slot 2
        serial_nums = ["105", "106"]
        axes = ["x", "y"]
        
        # Initialise the stepper motor as empty object
        self.sm = StepperMotor()
        
        # Set up the stepper motors to the relevant axes such that self.x,
        # self.y control the (x,y) axis of the stepper motors
        for d in devices:
            for sn, ax in zip(serial_nums, axes):
                # second tuple element contains stepper motor S/N
                serial = d[1]
                if str(serial).endswith(sn):
                    # Set up the relevant axis to the stepper motor serial number
                    print ("S/N:", str(serial), "assigned to the", ax, "axis")
                    setattr(self.sm, ax, apt.Motor(int(serial)))
        
        # Set velocity parameters for x, y axes
        self.sm.x.set_velocity_parameters( min_vel=0.0, accn=0.1, max_vel=0.2 )
        self.sm.y.set_velocity_parameters( min_vel=0.0, accn=0.1, max_vel=0.2 )
                
        # Set Backlash
#         self.sm.x.backlash_distance = 0.00999939
#         self.sm.y.backlash_distance = 0.00999939
        
        #=======================================================================
        # Print out our backlash settings
        #=======================================================================
        print ('x-axis backlash:', self.sm.x.backlash_distance)
        print ('y-axis backlash:', self.sm.y.backlash_distance)
        
#         relative_coords_motor = self.motor_position
        
        # Initialise piezo controller (COM17) for SWIR ethernet connection
        # Locally (COM6)
        self.pc = PiezoController(port='COM6')
        
        if logfile:
            # Calibrate the loss up to the VGA
            self.input_power = input_power # dBm
            
            # Append the time of the start of the measurement for a unique
            # file name
            time_str = dt.utcnow().strftime('%H.%M')
            filename = 'IME03_QCL_input_power_{}dBm_SWIR_Gratings_{}.txt'.format(input_power,time_str)
            
            # Generate our text file name
            self.log_file = dated_folder(filename)
        else:
            self.log_file = None
        
        # This keeps track of coordinates relative to start position for
        # z-correction using the peizo controller
        self.relative_coordinates = (0.0,0.0)
        
    @property
    def motor_position(self):
        '''
        Return the (x,y) coordinates of the stepper motor
        '''
        return (self.sm.x.position, self.sm.y.position) 
    
    @property
    def piezo_voltages(self):
        '''
        Return the voltages (x,y,z) of the piezo
        '''
        x = self.pc.get_voltage('x')
        y = self.pc.get_voltage('y')
        z = self.pc.get_voltage('z')
        return (x, y, z)
        
    @property
    def piezo_voltages_rel(self):
        '''
        Return the relative (x,y,z) positions of the piezo (between 0 and 1)
        '''
        max_volt = self.pc.MAX_VOLTAGE
        x = self.pc.get_voltage('x')/max_volt
        y = self.pc.get_voltage('y')/max_volt
        z = self.pc.get_voltage('z')/max_volt
        return (x, y ,z)
    
    def optical_signal(self):
        '''
        returns the optical signal in dBm
        '''
#         t = time()
        m = self.measure()
#         print ('Signal:', m)
#         print ('measuring took {:.4f} s'.format(time()-t))
        return m
    
    def zero_stepper_motor(self):
        '''
        Move the stepper motor to the (x,y) = (0,0)
        '''
        self.sm.x.position = 0.0
        # wait for movement to finish
        while self.sm.x.is_in_motion:
            pass
        
        self.sm.y.position = 0.0
        # wait for movement to finish
        while self.sm.y.is_in_motion:
            pass
    
    def move_absolute(self, x, y, verbose=False, measure=False):
        '''
        Move stepper motor to absolute coordinates in millimeters
        ---------
        input:
            x - x position (mm)
            y - y position (mm)
        '''
        _x, _y = self.motor_position
        if verbose:
            print ('(x,y): (',_x,_y,')')
            print ('(x\',y\'): (',x, y,')')
        
        # remove errors with trying to set a floating point error of (x,y)=(0,0)
        x = 0.0 if x < 1e-5 else x
        y = 0.0 if y < 1e-5 else y
        
        # Log signals and positions while we scan the grid
        signals = []
        coords = []
        
       
#         # Move x first
#         new_position = _x + m11*(_x - x)
        self.sm.x.position = x #new_position
        if measure:# and type(self.detector) is not detect_o_tron:
            # wait for movement to finish
            while self.sm.x.is_in_motion:
                pos = self.motor_position
                m = self.optical_signal()
#                 print (m)
                if not math.isnan(m):
                    signals.append(m)
                    coords.append(pos)   
        else:
            # wait for movement to finish
            while self.sm.x.is_in_motion:
                pass
        
        
        # Move y second
        self.sm.y.position = y 
        if measure:# and type(self.detector) is not detect_o_tron:
            while self.sm.y.is_in_motion:
                pos = self.motor_position
                m = self.optical_signal()
#                 print (m)
                if not math.isnan(m):
                    signals.append(m)
                    coords.append(pos)          
        else:
            # wait for movement to finish
            while self.sm.y.is_in_motion:
                pass
            
        if measure and signals:
            # Locate the optimal signal and coordinates if they exist
            max_signal = max(signals)
            max_signal_idx = signals.index(max_signal)
            optimal_coords = coords[max_signal_idx]
            return optimal_coords, max_signal
        else:
            # Otherwise return None
            return None, None
    
    def _round(self, x, y, decimal_places):
        '''
        Round x and y to a certain number of decimal places
        '''
        s = "{" + ":.{}f".format(decimal_places) + "}"
        return float(s.format(x)), float(s.format(y))
            
    def move_stepper(self, axis, distance, theta=-0.02730242675, z_correction=False, verbose=False):
        '''
        IME03 - A5 theta = 0.0393280, 0.0143796, 0.03629983 << 3rd Calibration
        Move stepper motor in an axis by a relative distance
        ---------
        input:
            axis - (str) "x" or "y"
            distance - (float) distance in microns to move. Negative values
                        correspond to moving in the reverse direction.
            theta - (float) angle in radians for compensating any chip alignment
                    offset. Can be found using the method calculate_transformation_angle
            verbose - (bool) display output of start and end coordinates 
        '''
        if axis not in ["x", "y"]:
            self.release()
            raise RuntimeError( "axis %s is not in the (x,y) plane" % axis )
        # convert the distance in microns into millimeters for the stepper motor 
        distance_in_mm = distance/1000.0
        # Wait for stepper motor operation to finish before calling next command 
        block = True
        
        # get current x, y positions
        x, y = self.motor_position
        
             
        # Transformation (clockwise)
        # Note identity transformation for arg theta = 0
        m11, m12 =  np.cos(theta), np.sin(theta)
        m21, m22 =  -np.sin(theta), np.cos(theta)
        
        
        if axis == 'x':
            if verbose:
                print ('moving in', axis, 'by', distance_in_mm, '(mm)')
                print ('(x,y): (',x,y,')')
                print ('(x\',y\'): (',x+distance_in_mm,y,')')
            
            # Update relative (to start position) stepper motor coordinates
            xr, yr = self.relative_coordinates
            xr = xr + m11*distance_in_mm
            yr = yr + m21*distance_in_mm
            self.relative_coordinates = (xr, yr)
            
            new_position = x + m11*distance_in_mm
            # Set new position to 0 if some floating point rounding error
            # that the stepper motor cannot handle
            new_position = 0.0 if new_position < 1e-5 else new_position
            
            self.sm.x.position = new_position
            
            # wait for movement to finish
            while self.sm.x.is_in_motion:
                pass
            
            # Y- correction
            new_position = y + m21*distance_in_mm
            new_position = 0.0 if new_position < 1e-5 else new_position
            self.sm.y.position = new_position
            # wait for movement to finish
            while self.sm.y.is_in_motion:
                pass
            
        else:
            if z_correction:
                ''' THIS Z-CORRECTION IS EXPERIMENTAL CURRENTLY '''
                # YMAX is the largest distance between test structures in Y
                YMAX = 2352.0 # um
                
                xr, yr = self.relative_coordinates
                xr = xr + m12*distance_in_mm
                yr = yr + m22*distance_in_mm
                self.relative_coordinates = (xr, yr)
                
                
                # Set the z voltage proportional to the max distance
                if (yr*1000)/YMAX > 1:
                    zrV = 1
                elif (yr*1000)/YMAX < 0:
                    zrV = 0
                else:
                    zrV = (yr*1000)/YMAX
                self.pc.set_voltage_rel('z', zrV)
            
            #===================================================================
            # z_compensation_um = distance/10.0
            # # roughly 2.5V per micron of actuation
            # z_compensation_V = z_compensation_um*2.5
            # z_V = self.pc.get_voltage('z')
            # new_z_V = z_V + z_compensation_V
            # self.pc.set_voltage('z', new_z_V)
            #===================================================================
            
            if verbose:
                print ('moving in', axis, 'by', distance_in_mm, '(mm)')
                print ('(x,y): (',x,y,')')
                print ('(x\',y\'): (',x,y+distance_in_mm,')')

            new_position = y + m22*distance_in_mm
            # Set new position to 0 if some floating point rounding error
            # that the stepper motor cannot handle
            new_position = 0.0 if new_position < 1e-5 else new_position
            
            self.sm.y.position = new_position
            
            # wait for movement to finish
            while self.sm.y.is_in_motion:
                pass
            
            # X-correction
            new_position = x + m12*distance_in_mm
            new_position = 0.0 if new_position < 1e-5 else new_position
            self.sm.x.position = new_position
            
            # wait for movement to finish
            while self.sm.x.is_in_motion:
                pass
            
    
    def search_for_signal(self, limits, step_size, search=False):
        '''
        Use stepper motor to scan over a range of x and y coordinates in
        1 micron steps
        ------
        input:
            limits - (int) in microns search from -limits/2 to limits/2 in x,y grid
            step_size - (float) microns step size increment for each point in x,y grid
        '''
        
        x, y = self.motor_position
        
        if not search:
            n_avg = 3
            # Average over a few optical signals
            signal_avg = sum([self.optical_signal() for _ in range(n_avg)])/n_avg
             
            print ('Coupling:', signal_avg)
             
            if signal_avg > self.noise_floor:
                return (x,y), signal_avg
        
   
        
        print ("##### SEARCHING FOR OPTICAL SIGNAL #####")
        
        step_size /= 1000.0 # convert microns to mm
        x_pos, y_pos = self.motor_position
        
        # set scan limits
        l = int(limits/2)
        x_scan = [x_pos + (x - l)*step_size for x in range(0, limits+1)] #range(1, limits+1)
        y_scan = [y_pos + (y - l)*step_size for y in range(0, limits+1)]#range(1, limits+1)
        
        n_points = len(x_scan)**2
        
        # initialise array recording position and optical signal
        coords = []
        signals = []
        
        print ('Starting scan...')
        n = 0
        for x in x_scan:
            print ('{:.1f}% complete'.format((n/n_points)*100))
            for y in y_scan:
                # search for optical signal whilst we move
                xy, signal = self.move_absolute(x, y, measure=True)
#                 print ('move_absolute best signal',signal)
                if (xy is not None) and (signal is not None):
                    signals.append(signal)
                    coords.append(xy)
                
                # Record signal at the end of the movement
                signal = self.optical_signal()
                if math.isnan(signal):
                    signal = self.noise_floor
#                 print ('optical signal {} dBm \n'.format(signal))
                signals.append(signal)
                coords.append(self.motor_position)
                n += 1
        
        # find array element with best signal
        best_signal_idx = signals.index(max(signals))
        
        eval_range = 7
        if eval_range < best_signal_idx < len(signals) - eval_range:
            print ('Checking for anomaly...')
            print ('max signal', max(signals))
            local_signals = signals[best_signal_idx-eval_range:best_signal_idx+eval_range]
            local_avg = sum(local_signals)/len(local_signals)
            print ('average about max signal', local_avg)
            if local_avg < 5*max(signals):
                print ('We have an anomaly!')
            else:
                print ('Everything checks out!')
            
            
        optimal_coords = coords[best_signal_idx]
        
        if max(signals) < self.noise_floor:
            return (x_pos, y_pos), self.noise_floor
        else:
            return optimal_coords, max(signals)

    
    def course_optimise(self):
        '''
        Use stepper motors to do low accuracy alignment with optical devices
        -----
        input:
            n_avg - (int) number of averages to take on the initial measurement
                    to determine if there is coupling or to peform signal search
        returns:
            True if a signal above the noise floor was found else False
        '''
        x, y = self.motor_position
        
        n_avg = 25
        # Average over a few optical signals
        signal_avg = sum([self.optical_signal() for _ in range(n_avg)])/n_avg

        
        # If we have a signal, then optimise!
        if signal_avg > self.noise_floor:
            print ('\n######## STARTING COURSE OPTIMISATION #######\n')
            print( 'Optimise in the +y direction' )
            coords_yp = [(x,y)]
            signals_y_plus = [signal_avg]
            
            # number of data points to measure for negative gradient termination
            grad_termination = 8
            
            step_size = 0.001 # (mm)
            overshoot = 0.01 # (mm)
            
            # Overshoot into the noise floor in -y direction
            y -= overshoot
            
            n = 0
            # Scan in y+ direction until we find something
            self.move_absolute(x, y)
            while self.optical_signal() <= self.noise_floor:
                y += step_size
                n +=1
                coords, signal = self.move_absolute(x, y, measure=True)
                if signal is not None:
                    if signal > self.noise_floor:
                        break
                if n > 2*(overshoot/step_size):
                    print ('\n######## DEVICE NOT FOUND ########\n')
                    return False
                
            # Log our first signal
            coords_yp.append((x,y))
            signals_y_plus.append(self.optical_signal())
            
            # Now we log until we hit the noise floor
            n_steps = 0
            while self.optical_signal() > self.noise_floor:
                y += step_size
#                 self.move_absolute(x, y)
                coords, signal = self.move_absolute(x, y, measure=True)
                if signal is not None:
                    if signal > self.noise_floor:
                        coords_yp.append(coords)
                        signals_y_plus.append(signal)
                coords_yp.append((x,y))
                signals_y_plus.append(self.optical_signal())
                n_steps += 1
                if n_steps > grad_termination:
                    grads = np.gradient(signals_y_plus[-grad_termination:])
                    # if on average our gradients are negative we can terminate
                    if sum(grads)/len(grads) < 0.0:
                        break
            
            # Now we choose the stepper motor coordinates which optimised the
            # signal
            if signals_y_plus:
                best_pos_y_plus = coords_yp[signals_y_plus.index(max(signals_y_plus))]
                _x , _y = best_pos_y_plus
            self.move_absolute(_x, _y)
            
            
            # Repeat for the x-direction
            print('Optimise in the +x direction')
            coords_xp = [(_x, _y)]
            x, y = _x , _y
            signals_x_plus = [self.optical_signal()]
            
            # Overshoot into the noise floor in -x direction
            x -= overshoot
            
            n = 0
            # Scan in x+ direction until we find something
            self.move_absolute(x, y)
            while self.optical_signal() <= self.noise_floor:
                x += step_size
                n += 1
#                 self.move_absolute(x, y)
                coords, signal = self.move_absolute(x, y, measure=True)
                if signal is not None:
                    if signal > self.noise_floor:
                        break
                if n > 2*(overshoot/step_size):
                    print ('\n######## DEVICE NOT FOUND ########\n')
                    return False
            coords_xp.append((x,y))
            signals_x_plus.append(self.optical_signal())
            
            n_steps = 0
            while self.optical_signal() > self.noise_floor:
                x += step_size
#                 self.move_absolute(x, y)
                coords, signal = self.move_absolute(x, y, measure=True)
                if signal is not None:
                    if signal > self.noise_floor:
                        coords_xp.append(coords)
                        signals_x_plus.append(signal)
                coords_xp.append((x,y))
                signals_x_plus.append(self.optical_signal())
                n_steps += 1
                if n_steps > grad_termination:
                    grads = np.gradient(signals_x_plus[-grad_termination:])
                    # if on average our gradients are negative we can terminate
                    if sum(grads)/len(grads) < 0.0:
                        break
                
            b = coords_yp + coords_xp
            s = signals_y_plus + signals_x_plus
            _x, _y = b[s.index(max(s))]
            self.move_absolute(_x, _y)
            sleep(5.0)
            print ('\n######## COURSE OPTIMISATION COMPLETE ######\n')
            return True
        else:
            print ('\n######## DEVICE NOT FOUND ########\n')
            return False
    
    def local_optimise(self):
        '''
        Optimise the optical power with piezos
        '''

        # define min and max voltage bounds s.t. they can't be exceeded
        V_MIN, V_MAX = 1.0, 74.0
        
        tol = 0.005 # tolerance : TODO loop?
        step_size = 0.5 # (V)
        x, y = self.piezo_voltages[:-1]
        
        # number of data points to measure for negative gradient termination
        grad_termination = 20
        
        signal = self.optical_signal()
        if  signal > self.noise_floor:
            
            print ('\n######## STARTING PIEZO OPTIMISATION #######\n')
            print( 'Optimise in the +y direction' )
            coords_yp = [(x,y)]
            signals_y_plus = [signal]
            
            
            n_steps = 0
            while self.optical_signal() > self.noise_floor:
                y += step_size
                if not V_MIN < y < V_MAX: break
                self.pc.set_voltage('y', y)
                coords_yp.append((x,y))
                signals_y_plus.append(self.optical_signal())
                n_steps += 1
                if n_steps > grad_termination:
                    grads = np.gradient(signals_y_plus[-grad_termination:])
                    # if on average our gradients are negative we can terminate
                    if sum(grads)/len(grads) < 0.0:
                        break
                
            if signals_y_plus:
                best_pos_y_plus = coords_yp[signals_y_plus.index(max(signals_y_plus))]
                _x , _y = best_pos_y_plus
            self.pc.set_voltage('x', _x)
            self.pc.set_voltage('y', _y)
            
            print ('Optimise in the -y direction' )
            coords_ym = [(_x, _y)]
            x, y = _x, _y
            signals_y_minus = [self.optical_signal()]
            
            
            n_steps = 0          
            while self.optical_signal() > self.noise_floor:
                y -= step_size
                if not V_MIN < y < V_MAX: break
                self.pc.set_voltage('y', y)
                coords_ym.append((x, y))
                signals_y_minus.append(self.optical_signal())
                n_steps += 1
                if n_steps > grad_termination:
                    grads = np.gradient(signals_y_minus[-grad_termination:])
                    # if on average our gradients are negative we can terminate
                    if sum(grads)/len(grads) < 0.0:
                        break
                
                
            if signals_y_minus:
                best_pos_y_minus = coords_ym[signals_y_minus.index(max(signals_y_minus))]
                _x , _y = best_pos_y_minus
            else:
                _x , _y = best_pos_y_plus
            self.pc.set_voltage('x', _x)
            self.pc.set_voltage('y', _y)
            
            print('Optimise in the +x direction')
            coords_xp = [(_x, _y)]
            x, y = _x, _y
            signals_x_plus = [self.optical_signal()]
            
            
            n_steps = 0
            while self.optical_signal() > self.noise_floor:
                x += step_size
                if V_MIN < x < V_MAX: break
                self.pc.set_voltage('x', x)
                coords_xp.append((x,y))
                signals_x_plus.append(self.optical_signal())
                n_steps += 1
                if n_steps > grad_termination:
                    grads = np.gradient(signals_x_plus[-grad_termination:])
                    # if on average our gradients are negative we can terminate
                    if sum(grads)/len(grads) < 0.0:
                        break
                
            if signals_x_plus:
                best_pos_x_plus = coords_xp[signals_x_plus.index(max(signals_x_plus))]
                _x , _y = best_pos_x_plus
            else:
                b = coords_yp + coords_ym
                s = signals_y_plus + signals_y_minus
                _x, _y = b[s.index(max(s))]
            self.pc.set_voltage('x', _x)
            self.pc.set_voltage('y', _y)
            
            print('Optimise in the -x direction')
            coords_xm = [(_x,_y)]
            x, y = _x, _y
            signals_x_minus = [self.optical_signal()]
            
            
            n_steps = 0
            while self.optical_signal() > self.noise_floor:
                x -= step_size
                if not V_MIN < x < V_MAX: break
                self.pc.set_voltage('x', x)
                coords_xm.append((x,y))
                signals_x_minus.append(self.optical_signal())
                n_steps += 1
                if n_steps > grad_termination:
                    grads = np.gradient(signals_x_minus[-grad_termination:])
                    # if on average our gradients are negative we can terminate
                    if sum(grads)/len(grads) < 0.0:
                        break

            b = coords_yp + coords_ym + coords_xp + coords_xm
            s = signals_y_plus + signals_y_minus + signals_x_plus + signals_x_minus
            _x, _y = b[s.index(max(s))]
            self.pc.set_voltage('x', _x)
            self.pc.set_voltage('y', _y)
        
        print ('\n######## PIEZO OPTIMISATION COMPLETE ######\n')
    
    def optimise(self, n_course=1, n_fine=1, signal_search=False, term_early=False):
        '''
        Run course grain and fine grain optimisation using the stepper motors
        and the piezos to optimise the optical signal
        ------
        inputs:
            n_course - (int) number of times to run course optimisation
            n_fine - (int) number of times to run fine grain optimisation
        returns:
            True if a device is coupled and False if not
        '''
        
        coords, signal = self.search_for_signal(8, 6, search=signal_search)
        print ('signal search coords: {}, signal: {:.2f} {}'.format(coords, signal, self.UNITS))
        x, y = coords
        self.move_absolute(x, y)

        # TODO; VERIFY THIS EXPERIMENTAL IF CLAUSE
        if term_early:
            sleep(7.0)
            n_avg = 25
            signal = sum([self.optical_signal() for _ in range(n_avg)])/n_avg
            if signal < self.noise_floor:
                print ('Failed to find device')
    #             self.move_absolute(x, y)
                return False
        
        if n_course == 0:
            device_found = True
        
        for _ in range(n_course):
            device_found = self.course_optimise()
            if not device_found:
                return False
        
        if device_found:
            for _ in range(n_fine):
                self.local_optimise()
        
        return True
    
    def reset_piezo(self, mm_per_V=0.000417):
        '''
        Half the x,y values of the piezos and compensate the value by changing
        the stepper motors.
        
        30 microns of travel from 0 V --> 75 V i.e. 0.4 um/V
        mm_per_V - (float) default to 0.000417 as given by calibration function
        --------
        input:
            mm_per_V - (float) number of millimeters to compensate on the stepper
                        moters to per Volt of the piezo stage
        '''
        # Set up constants
        V_MAX = self.pc.MAX_VOLTAGE
        half_V = V_MAX/2.0
        
        # In microns?
        microns = False
        um_per_volt = 0.4 # um/V
        
        # in millimeters (from calibration and default arg)
        
        # get x,y piezo voltages
        x_V, y_V = self.piezo_voltages[:-1]
        # difference between current voltage and halfway point
        dx_V, dy_V = half_V - x_V, half_V - y_V
        
        if microns:
            # convert distance to microns
            dx, dy = dx_V*um_per_volt, dy_V*um_per_volt
            
            # compensate the stepper motors
            if dx > 0.4: 
                self.move_stepper('x', dx)
            if dy > 0.4:
                self.move_stepper('y', dy)
        else:
            if abs(dx_V) > 0.4 or abs(dy_V) > 0.4:  
                dx, dy = dx_V*mm_per_V, dy_V*mm_per_V
                x, y = self.motor_position
                self.move_absolute(x - dx, y - dy)
            
        print ('\n###### RESET PIEZOS TO HALF VOLTAGES ########\n')
        # reset the piezos to half their values
        self.pc.half_xy_axes()
    
    def calibrate_stepper_motor_and_piezo(self):
        '''
        Calculate the voltage to stepper motor distance compensation. This
        function assumes that there is coupling into a grating 
        ------
        returns:
            The calibration of the millimeters per volt
        '''
        # Lets zero the piezos
        self.pc.half_xy_axes()
        # First do a stepper motor optimisation signal on a grating coupler
        self.course_optimise()
        
        # Find the old stepper motor coordinates
        x_old, y_old = self.motor_position
        
        # Get and set piezo voltages
        y_V = self.pc.get_voltage('y')
        # Now lets offset the piezo voltages by a voltage offset
        V_offset = 30.0
        self.pc.set_voltage('y', y_V - V_offset)
        sleep(1.0)
        
        # And compensate with the stepper motor to figure out the
        # distance
#         x, y = self.motor_position
        print ('Moving back in Y')
        y_offset = y_old + 0.04
        # Decrease the velocity parameters in y
        self.sm.y.set_velocity_parameters( min_vel=0.0, accn=0.005, max_vel=0.001 )
        coords, signal = self.move_absolute(x_old, y_offset, verbose=True, measure=True)
        self.sm.y.set_velocity_parameters( min_vel=0.0, accn=0.1, max_vel=0.2 )
        sleep(2.0)
        if coords is None:
            print ('Device not found')
            return
        
        # The stepper motor compensation for 20V offset in y-axis is
        x_opt, y_opt = coords
        dy = y_old - y_opt
        
        # distance per unit volt is
        piezo_and_stepper_calib = abs(dy/V_offset)
        
        # For now lets assume that x has the same Volts/distance (mm)
        
        print ('Piezo to stepper motor calibration in Y axis:', piezo_and_stepper_calib , 'mm/V')
        return piezo_and_stepper_calib
    
    
    def calculate_transformation_angle(self, axis, distance):
        '''
        Move between two adjacent pairs of grating couplers using the stepper
        motors. Calculate the difference between our expected endpoint
        and the optimised end point --> calculate the transformation matrix.
        Note the initial position should be optimised first before running
        this method!
        ------
        input:
            axis - (str) ['x', 'y']
            distance - (float) distance in microns between the two gratings
        return:
            Vector of transformation matrix M corresponding to the axis
        '''
        if axis not in ['x', 'y']:
            self.release()
            raise RuntimeError('Axis %s is not in the x-y plane' % axis)
        
        # The number of times to run course grain optimisation on the
        # adjacent grating coupler
        N = 2
        
        # Log the initial positions
        x_start, y_start = self.motor_position
        
        # Now lets move to the next grating
        self.move_stepper(axis, distance, theta=0)
        
        # Run course optimisation N times
        device_found = self.optimise(n_course=N, n_fine=0, signal_search=True)
        if not device_found:
            return None, None, None
        
        # Get our final positions
        x_final, y_final = self.motor_position
        
        # Calculate where difference from our start and end points
        dx = x_final - x_start
        dy = y_final - y_start
        
        # Calculate our transformations
        L = np.sqrt(dx**2 + dy**2)
        if axis == 'x':
            theta = np.arcsin(dx/L)
            return theta

        else:
            theta = np.arccos(dy/L)
            return theta
      
    
    def release(self):
        '''
        Free up the peizo (pyserial) and the detector (websocket/pyvisa) 
        '''
        print ('###################################')
        print ('Releasing USB/COM ports')
        print ('###################################')
        if self.monochromator is not None and self.wavelength_offset != 0.0:
            print ('Resetting monochromator to initial position')
            self.monochromator.goto_wavelength(0.0)
        self.pc.close_connection()
        
        if type(self.detector) is Powermeter:
            self.detector.__del__()
        
        elif type(self.detector) is detect_o_tron:
            self.detector.close()
        
        print ('... done!')
    
    def measure_spectrum(self, filename, prefix = '', timing_window = 0.5, wavelength_plus_minus = 75):
        '''
        Measure the spectral response of the device using the monochromator
        --------
        input:
            filename - (str) the string of the test structure being measured
            prefix - (str) any additional information about the test structure
                    measurement.
        returns:
            *.csv and *.pdf file into the Data folder (note this is relative data)
            and requires a calibration file of the same step size for a known
            reference laser (e.g. 2050 nm QCL )
        '''
        
        if self.wavelength_offset != 0.0:
            print ('Moving monochromator back to zero')
            self.monochromator.goto_wavelength(0.0)
        
        min_lambda = -wavelength_plus_minus # nm (relative)
        max_lambda = wavelength_plus_minus # nm  (relative)
        nm_step_size = 1./3. # nm
        
        if type(self.detector) is detect_o_tron:
            self.detector.update_timing_window(timing_window)
            
        print ('########### MEASURING SPECTRA ############')
        
        monochromator.scan_monochromator(filename_suffix = prefix + filename,
                                       measure_func = self.measure,
                                       detector = self.detector,
                                       monochromator = self.monochromator,
                                       aperture = 'SMF-28',
                                       range_nm = (min_lambda, max_lambda),
                                       nm_step = nm_step_size,
                                       antibacklash_steps = 90)
        
        print ('############### COMPLETE! ################')
        
        if type(self.detector) is detect_o_tron:
            self.detector.update_timing_window(0.1)
        
        if self.wavelength_offset != 0.0:
            print ('moving to {} nm'.format(self.wavelength_offset))
            self.monochromator.goto_wavelength(self.wavelength_offset)
        

    def record_power(self, device_ID, x0, y0, n_avg = 100):
        '''
        log the optical power to a txt file, averaged over a number of
        measurements
        ---------
        input:
            device_ID - (str) string to uniquely identify the device
            n_avg - (int) number of times to average the signal
        returns:
            logs to the data folder using the name self.log_file 
        '''
        measurement = sum([self.optical_signal() for _ in range(n_avg)])/n_avg
        with open(self.log_file, 'a') as f:
            x, y = self.motor_position
            _x, _y = x - x0, y - y0
            f.write('{}\t{:.4f}\t ({:.5f},{:.5f})\n'.format(device_ID, measurement - self.input_power, _x, _y))
            
        

    def scan_array(self, x_pitch, y_pitch, N, M, device_names, prefix='', n_course=2, n_fine=2):
        '''
        Scan array of gratings
            - assume that rough alignment has coupled into the top right of the
            grating block.
            - assume that the transformation matrix and piezo <=> stepper motor
            calibrations have been run
        --------
        x_pitch - (float) distance in microns between the grating in the x direction
        y_pitch - (list) distance to travel between adjacent sets of grating couplers
        N - (int) number of times to iterate through the x_pitch
        M - (int) number of times to iterate through the y_pitch
        device_names - (list) strings corresponding to the label given to the device
                        when the spectra/loss measurement is taken
        prefix - (str) string prefix of the device name specifying any additional
                        information about the measurement. Default is an empty string
        n_course - (int) number of times to run course optimisation (stepper motors)
        n_fine - (int) number of times to run fine grain optimisation (piezos)
        '''
        if self.log_file is not None:
            print ('Logging our results to {}'.format(self.log_file))
            
            with open(self.log_file, 'w') as f:
                if type(self.detector) is Powermeter:
                    f.write('Grating ID\t Loss (dB) \t Position (rel mm)\n')
                elif type(self.detector) is detect_o_tron:
                    f.write('Grating ID\t Power (Hz)\t Position (rel mm)\n')
        
        x0, y0 = self.motor_position
        d = 0
        
        print ('############### STARTING ARRAY SCAN #################')        
        for n in range(N):
            # Optimise for optical signal
            name = device_names[d]
            print ('\n********** NEXT DEVICE {} ***********'.format(name))
            device_found = self.optimise(n_course, n_fine, term_early=True)
            
            # scan_monochromtor
            if self.monochromator is not None and device_found:
                self.measure_spectrum(name, prefix)
            if self.log_file is not None and device_found:
                self.record_power(name, x0, y0)
            d += 1
            
            
            for m in range(M):
                g = 1
                # Move to adjacent gratings
                for y in y_pitch:
                    
                    if m == M-1 and g == len(y_pitch):
                        # Don't move to the next gratings over if we have
                        # measured our last grating set
                        break
                    elif m == 0 and n%2 == 1:
                        # Don't move by to next grating pair if we have
                        # reversed the direction towards origin
                        break
                    
                    # Set piezos to half of max voltage
                    self.reset_piezo()
                    
                    # Reverse the direction on odd iterations of the x_pitch
                    y = y if n%2 == 0 else -y
                    
                    # Move to next grating
                    self.move_stepper('y', y, z_correction=False)
                    
                    # Optimise for optical signal
                    name = device_names[d]
                    print ('\n********** NEXT DEVICE {} ***********'.format(name))
                    device_found = self.optimise(n_course, n_fine, signal_search = False, term_early = True)
                    
                    # scan_monochromator
                    if self.monochromator is not None and device_found:
                        self.measure_spectrum(name, prefix)
                    if self.log_file is not None and device_found:
                        self.record_power(name, x0, y0)
                        
                    print ('\n******* ARRAY SCAN {:.2f} % COMPLETE *******'.format(((d+1)/len(device_names))*100))
                    d += 1
                    g += 1
            
            # Now we move in x!
            self.reset_piezo()
            
            # Move to next grating
            self.move_stepper('x', -x_pitch)
            y_pitch.reverse()
    
        # Finally move back to original position
        self.move_absolute(x0, y0)
        
        print ('############### ARRAY SCAN COMPLETED #################')

    def visit_coordinates(self, coords_list, device_names, prefix=''):
        '''
        Given a list of absolute coordinates [(x1, y1), (x2, y2), ...], visit
        the locations and measure the spectrum/transmission power
        ------
        Input:
            coord_list - (list) tuples (x,y) specifying the absolute coordinates
                        in mm
            device_names - (list) strings that are used to identify the spectra
            prefix - (str) any other data that will be recorded in the filename
        '''
        
        if len(coords_list) != len(device_names):
            raise RuntimeError("""The length of the coordinate list and device
                                    labels is not the same""")
        
        x0, y0 = self.motor_position
        
        find_everything = []
        
        test = False
        
        for name, coords in zip(device_names, coords_list):
            
            print ('######## Moving to {} #########'.format(name))
            x, y = coords
            self.move_absolute(x, y)
            sleep(1.0)
            device_found = True if self.optical_signal() > self.noise_floor else False
            print ('Device found? {}'.format(device_found))
            
            if self.log_file is not None and not test:
                print ('Logging optical coupling')
                self.record_power(name, x0, y0)
            
            if self.monochromator is not None and not test:
                print ('Measuring spectrum...')
                self.measure_spectrum(name, prefix)
                print ('Done!')
            
            find_everything.append(device_found)
        
        print ('Returning to initial position\n\n')
        self.move_absolute(x0, y0)
        
        for found in find_everything:
            if not found:
                print ('missed a device!')
                break
        
        print (device_names)
        print (find_everything)