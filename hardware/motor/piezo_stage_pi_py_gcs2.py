# -*- coding: utf-8 -*-

"""
This file contains the PI Piezo hardware module for Qudi
through offical python moudle "PIPython" created by PI.

Copyright (c) 2019 diamond2nv@GitHub with GPLv3 License.

#1.

Physik Instrumente (PI) General Command Set 2 (GCS 2), 
"for all controllers". 

PIPython is a collection of Python modules to access a PI 
device and process GCS data. 
It can be used with Python 3.4+ (3.6.5) on Windows, Linux and 
OS X and without the GCS DLL also on any other platform.

This module file is tested with PIPython Version: 1.3.9.40 

PIPython Installation:
---------------------
Zip of PIPython for "python start.py install" should be in 
the CD with new PI controller device.

PIPython Copyright (c) General Software License Agreement 
of Physik Instrumente (PI) GmbH & Co. KG. See more at 
<https://www.physikinstrumente.com/en/products/motion-control-software/programming/>

You can connect via these interfaces with the according methods.
    
    USB: EnumerateUSB(mask='')
    TCPIP: EnumerateTCPIPDevices(mask='')

    RS-232: ConnectRS232(comport, baudrate)
    USB: ConnectUSB(serialnum)
    TCP/IP: ConnectTCPIP(ipaddress, ipport=50000)
    TCP/IP: ConnectTCPIPByDescription(description)
    NI GPIB: ConnectNIgpib(board, device)
    PCI board: Connect(board)

Unknown PI devices:
------------------

When you call GCSDevice with the controller name the 
according GCS DLL is chosen automatically. For unknown 
devices you can specify a dedicated GCS v2 DLL instead:

from pipython import GCSDevice
pidevice = GCSDevice(gcsdll='PI_GCS2_DLL.dll')


#2.

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

Qudi Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

#import numpy as np
#import ctypes
import time

from collections import OrderedDict

#PI Stage
from pipython import GCSDevice
from pipython import GCSError, gcserror
#from pipython import pitools, datarectools
pidevice = GCSDevice()

from core.module import Base, ConfigOption

#from interface.confocal_scanner_interface import ConfocalScannerInterface
#TODO：Trigger-Gate Confocal Scanner （Need PI Controller Set TTL Sync Output 
# to NI Card or Time Tagger or PYNQ Z2...) 

from interface.motor_interface import MotorInterface

class PiezoStagePI_PyGCS2(Base, MotorInterface):
    """ This is the hardware module for the PI GCSdevice in Qudi,
        driven by PI offical python moudle "PIPython",
        that can support almost all PI Piezo Stage Controller, 
        such as: E-516, E-727...

    !!!!!! PI GCS V2 DEVICES ONLY!!!!!!

    See PIPython for details, should be in the CD with new PI controller device.

    unstable: diamond2nv@GitHub

    This is intended as Confocal PI Piezo Scanner Hardware module
    that can be connected to confocal_scanner_motor_interfuse logic.

    Example config for copy-paste:

    piezo_stage_nanos:
        module.Class: 'motor.piezo_stage_pi_py_gcs2.PiezoStagePI_PyGCS2'
        pi_controller_mask: 'E-727'
        pi_piezo_stage_mask: 'P-563'

        first_axis_label: 'x'
        second_axis_label: 'y'
        third_axis_label: 'z'

        first_axis_ID: '1'
        second_axis_ID: '2'
        third_axis_ID: '3'

        first_min: 0e-6 # in m
        first_max: 300e-6 # in m
        second_min: 0e-6 # in m
        second_max: 300e-6 # in m
        third_min: 0e-6 # in m
        third_max: 300e-6 # in m

        first_axis_step: 1e-9 # in m
        second_axis_step: 1e-9 # in m
        third_axis_step: 1e-9 # in m

    
    """

    _modtype = 'PiezoStagePI_PyGCS2'
    _modclass = 'hardware'

    #Need to communicate with piezo controller to confirm enable or not.
    _has_connect_piezo = False
    _has_move_abs = False
    _has_move_rel = False
    _has_abort = False
    _has_get_pos = False
    _has_calibrate = False
    _has_get_velocity = False
    _has_set_velocity = False

    #default servo on for xyz
    _default_servo_state = [True, True, True]


    unit_factor = 1e6 # This factor converts the values given in m to um.
    ### !!!!! Attention the units can be changed by setunit

    #TODO: config options, like other motor hardware
    _pi_controller_mask = ConfigOption('pi_controller_mask', 'E-727', missing='warn')
    _pi_piezo_stage_mask = ConfigOption('pi_piezo_stage_mask', 'P-563', missing='warn')

    _first_axis_label = ConfigOption('first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('second_axis_label', 'y', missing='warn')
    _third_axis_label = ConfigOption('third_axis_label', 'z', missing='warn')
    #_fourth_axis_label = ConfigOption('fourth_axis_label', 'a', missing='warn')
    _first_axis_ID = ConfigOption('first_axis_ID', '1', missing='warn')
    _second_axis_ID = ConfigOption('second_axis_ID', '2', missing='warn')
    _third_axis_ID = ConfigOption('third_axis_ID', '3', missing='warn')
    #_fourth_axis_ID = ConfigOption('fourth_axis_ID', '4', missing='warn')

    _min_first = ConfigOption('first_min', 0e-6, missing='warn')
    _max_first = ConfigOption('first_max', 100e-6, missing='warn')
    _min_second = ConfigOption('second_min', 0e-6, missing='warn')
    _max_second = ConfigOption('second_max', 100e-6, missing='warn')
    _min_third = ConfigOption('third_min', 0e-6, missing='warn')
    _max_third = ConfigOption('third_max', 100e-6, missing='warn')
    #_min_fourth = ConfigOption('fourth_min', 0e-6, missing='warn')
    #_max_fourth = ConfigOption('fourth_max', 0e-6, missing='warn')

    step_first_axis = ConfigOption('first_axis_step', 1e-9, missing='warn')
    step_second_axis = ConfigOption('second_axis_step', 1e-9, missing='warn')
    step_third_axis = ConfigOption('third_axis_step', 1e-9, missing='warn')
    #step_fourth_axis = ConfigOption('fourth_axis_step', 1e-9, missing='warn')

    #_vel_min_first = ConfigOption('vel_first_min', 1e-9, missing='warn')
    #_vel_max_first = ConfigOption('vel_first_max', 1e-3, missing='warn')
    #_vel_min_second = ConfigOption('vel_second_min', 1e-9, missing='warn')
    #_vel_max_second = ConfigOption('vel_second_max', 1e-3, missing='warn')
    #_vel_min_third = ConfigOption('vel_third_min', 1e-9, missing='warn')
    #_vel_max_third = ConfigOption('vel_third_max', 1e-3, missing='warn')
    #_vel_min_fourth = ConfigOption('vel_fourth_min', 1e-5, missing='warn')
    #_vel_max_fourth = ConfigOption('vel_fourth_max', 5e-2, missing='warn')

    _vel_step_first = ConfigOption('vel_first_axis_step', 2e-6, missing='warn')
    _vel_step_second = ConfigOption('vel_second_axis_step', 2e-6, missing='warn')
    _vel_step_third = ConfigOption('vel_third_axis_step', 2e-6, missing='warn')
    #_vel_step_fourth = ConfigOption('vel_fourth_axis_step', 2e-6, missing='warn')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Open connection with PI Controller through PIPython module. 
    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        try:
            self._configured_constraints = self.get_constraints()
            #TODO: get_constraints by question with controller
            pidevice.errcheck = True

            #FIXME This will trigger a GUI, shoud be taken by Qudi GUI.
            #pidevice.InterfaceSetupDlg('pidevice_token')
            #pidevice = GCSDevice('E-727')
            #pidevice.ConnectTCPIP('192.168.178.42')
            try:
                devices = pidevice.EnumerateUSB(mask=self._pi_controller_mask)
                self.log.warning("PI ConnectUSB Devices:" + str(devices))
                if len(devices) is not 0:
                    pidevice.ConnectUSB(devices[0])
                    self._has_connect_piezo = True                    
            except:
                try:
                    devices = pidevice.EnumerateTCPIPDevices(mask=self._pi_controller_mask)
                    self.log.warning("PI ConnectTCPIP Devices:" + str(devices))
                    if len(devices) is not 0:
                        pidevice.ConnectTCPIPByDescription(devices[0])
                        self._has_connect_piezo = True                        
                except:
                    pass

            if self._has_connect_piezo:
                device_name = pidevice.qIDN()
                self._set_servo_state(True)
                self.log.info('Activate Motor and Set servo on for PI Controller = {}'.format(device_name.strip()))

            else:
                self.log.error("Not Found PI Controller = {} !".format(self._pi_controller_mask))
                return -1
        except GCSError as exc:
            self.log.error("PI GCSError: " + str(GCSError(exc)))
            return -1
            #raise GCSError(exc)
        except IndexError:
            self.log.error("Not Found PI Controller = {} !".format(self._pi_controller_mask))
            return -1
        except:
            self.log.error("Not Activate Motor!")
            return -1

        if self._has_connect_piezo:
            try:
                self._has_move_abs = pidevice.HasMOV()
                self._has_get_pos = pidevice.HasqPOS()
                #self._configured_constraints = self.get_constraints()
                #above is important to logic interfuse motor scanner

                if self._has_move_abs and self._has_get_pos:
                    try:
                        self._has_move_rel = pidevice.HasMVR()
                        self._has_abort = pidevice.HasStopAll()            
                        self._has_calibrate = pidevice.HasATZ()
                        self._has_get_velocity = pidevice.HasqVEL()
                        self._has_set_velocity = pidevice.HasVEL()
                        # above is not as important as MOV() and qPOS() in motor-scanner-interfuse
                    except GCSError as exc:
                        self.log.warning("PI GCSError: " + str(GCSError(exc)))
                        pass
                    finally:
                        return 0
                else:
                    self.log.error("PI Device has no MOV() or qPOS() func !")
                    return -1

                pidevice.errcheck = False
                # If communication speed like MOV() for motor scanner is an issue, you can disable error checking.
            except:
                self.log.error("PI GCSError: " + str(GCSError(exc)))
                return -1


    def on_deactivate(self):
        """ Deinitialise and deactivate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        #TODO add def shutdown(self) to set Votage=0 V for safety.
        #self._set_servo_state(False)
        #If not shutdown, keep servo on to stay on target.
        pidevice.errcheck = True
        try:
            pidevice.CloseConnection()
            self.log.warning("PI Device Close Connection !")
            return 0
        except GCSError as exc:
            self.log.error("PI GCSError: " + str(GCSError(exc)))
            return -1

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)

            @return dict constraints : dict with constraints for the device
        """
        #TODO get constraints auto by gcs

        constraints = OrderedDict()

        axis0 = {'label': self._first_axis_label,
                 'ID': self._first_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_first,
                 'pos_max': self._max_first,
                 'pos_step': self.step_first_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis1 = {'label': self._second_axis_label,
                 'ID': self._second_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_second,
                 'pos_max': self._max_second,
                 'pos_step': self.step_second_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis2 = {'label': self._third_axis_label,
                 'ID': self._third_axis_ID,
                 'unit': 'm', 
                 'ramp': None,
                 'pos_min': self._min_third,
                 'pos_max': self._max_third,
                 'pos_step': self.step_third_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        #constraints[axis3['label']] = axis3

        return constraints

    def move_rel(self, param_dict):
        """ Move stage relatively in given direction

            @param dict param_dict : dictionary, which passes all the relevant
                                     parameters, which should be changed. Usage:
                                     {'axis_label': <the-abs-pos-value>}.
                                     'axis_label' must correspond to a label given
                                     to one of the axis.


            @return dict param_dict : dictionary with the current magnet position
        """
        if self._has_move_rel:
            try:
                new_param_dict = self._axis_dict_send(param_dict)
                pidevice.MVR(new_param_dict)
                #Send str upper + um: X Y Z
            except:
                self.log.warning("PI move_rel / MVR failed !")
        else:
            self.log.warning('PI MVR Function not yet implemented')

        return param_dict

    def move_abs(self, param_dict):
        """ Move the stage to an absolute position

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                 The values for the axes are in meter,
                                 the value for the rotation is in degrees.

        @return dict param_dict : dictionary with the current axis position
        """
        # pidevice.MOV or pidevice.MVT is better ?
        if self._has_move_abs:
            try:
                new_param_dict = self._axis_dict_send(param_dict)
                pidevice.MOV(new_param_dict)
                #Send str upper + um: X Y Z
            except:
                self.log.warning("PI move_abs failed !")
        else:
            self.log.warning('PI MOV Function not yet implemented')

        return param_dict

    def abort(self):
        """ Stop movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        # Not pidevice.SystemAbort(): will cause halt or reboot.
        if self._has_abort:
            try:
                pidevice.StopAll()
                pidevice.errcheck = True
                return 0
            except GCSError as exc:
                self.log.error("PI GCSError: " + str(GCSError(exc)))
                #raise GCSError(exc)
                return -1
        else:
            self.log.warning('PI System Abort/StopAll Function not yet implemented')
            return 0

    def get_pos(self, param_list=None):
        """ Get the current position of the stage axis

        @param list param_list : optional, if a specific position of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then the positions of
                                 all axes are returned.

        @return dict param_dict : with keys being the axis labels and item the current
                                  position.
        """
        param_dict = {}
        if self._has_get_pos:
            try:
                pidevice.qPOS(param_dict)
                # axis dict get conversion 
                param_dict = self._axis_dict_get(param_dict)
            except:
                self.log.warning("PI get_pos failed !")
            finally:
                return param_dict
        else:
            self.log.warning('PI qPOS() Function not yet implemented')
            return param_dict

    def on_target(self, param_list=None):
        """ Stage will move all axes to targets 
        and waits until the motion has finished.
        Maybe useful in scan line began.

        @param list param_list : optional, if a specific status of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then from each axis the
                                 status is asked.

        @return int: error code (0:OK, -1:error)
        """
        if param_list is None:        
            for i in range(10):
                if not all(list(pidevice.qONT().values())):
                    time.sleep(0.1)
                    i += 1
                    if i >= 9:
                        return -1
                        #over time
                else:
                    return 0

        else:
            self.log.warning('PI qONT(param_list) not yet implemented, use qONT() only, for now.')
            time.sleep(0.1)
            return 0
        

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list : optional, if a specific status of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then from each axis the
                                 status is asked.

        @return dict : with the axis label as key and the status number as item.
            The meaning of the return value is:
            Bit 0: Ready 
            Bit 1: On target 
            Bit 2: Reference drive active 
            Bit 3: Joystick ON --- pidevice.qJON #TODO
            Bit 4: Macro running 
            Bit 5: Motor OFF 
            Bit 6: Brake ON 
            Bit 7: Drive current active
        """
        #TODO
        self.log.info('Not yet implemented for this hardware')

    def calibrate(self, param_list=None):
        """ Calibrate the stage.

        @param dict param_list : param_list: optional, if a specific calibration
                                 of an axis is desired, then the labels of the
                                 needed axis should be passed in the param_list.
                                 If nothing is passed, then all connected axis
                                 will be calibrated.

        After calibration the stage moves to home position which will be the
        zero point for the passed axis.

        @return dict pos : dictionary with the current position of the ac#xis
        """
        
        param_dict = {}

        if self._has_calibrate:
            try:
                pidevice.StopAll()
                pidevice.errcheck = True
                pidevice.ATZ()
                #PI Piezo Auto To Zero Calibration, just do it after power shutdown.
                param_dict = pidevice.qATZ()
                #has ATZ(), also should has qATZ()
            except GCSError as exc:
                self.log.error("PI GCSError: " + str(GCSError(exc)))
                #raise GCSError(exc)
            finally:
                return param_dict
        else:
            self.log.warning('PI Auto To Zero Function not yet implemented')
            return param_dict


    def get_velocity(self, param_list=None):
        """ Get the current velocity for all connected axes in m/s.

            @param list param_list : optional, if a specific velocity of an axis
                                     is desired, then the labels of the needed
                                     axis should be passed as the param_list.
                                     If nothing is passed, then from each axis the
                                     velocity is asked.

            @return dict : with the axis label as key and the velocity as item.
        """
        #TODO
        #param_dict = {}
        #pidevice.qVEL(param_dict)
        self.log.warning('PI get velocity function not yet implemented for this stage')

    def set_velocity(self, param_dict):
        """ Write new value for velocity in m/s.

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return dict param_dict2 : dictionary with the updated axis velocity
        """
        #TODO
        #pidevice.VCO axis is "on"
        #pidevice.VEL(param_dict)
        self.log.warning('PI set velocity function not yet implemented for this hardware')

########################## internal methods ##################################

    def _set_servo_state(self, to_state=None):
        """ Set the servo state (internal method)

            @param bool to_state : desired state of the servos,
                                   default servo state is True
        """
        servo_state = self._default_servo_state

        axis_list = ['1', '2', '3']

        if to_state is True or False:
            servo_state = [to_state, to_state, to_state]
        else:
            servo_state = self._default_servo_state
            #default servo on
            self.log.warning("""PI set servo state value None! 
            Shoud be True or False. Set to default servo state.""")

        try:
            pidevice.SVO(axis_list,servo_state)
        except:
            self.log.error("PI XYZ axis servo on failed!")

    def _axis_dict_send(self, param_dict):
        """ Set the capitalization axis label to str upper().
        #FIXME: Maybe not necessary for PIPython module

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        
        new_dict = {}
        for i, j in param_dict.items():
            new_dict[i.upper()] = j * self.unit_factor
            #str upper: X Y Z A
            # unit conversion from communication: m to um

        return new_dict

    def _axis_dict_get(self, param_dict):
        """ Set the capitalization axis label to str lower().

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        new_dict = {}
        for i, j in param_dict.items():
            new_dict[i.upper()] = j / self.unit_factor

            #str lower: x y z a
            # unit conversion from communication: um to m

        return new_dict