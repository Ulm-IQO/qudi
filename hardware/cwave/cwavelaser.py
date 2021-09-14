# -*- coding: utf-8 -*-

from core.module import Base
from core.configoption import ConfigOption
import math
import random
import time
from ctypes import c_char_p, CDLL, c_int
import os
from types import SimpleNamespace
from qtpy import QtCore
RegMode_dict = {'OFF':0, 
        'SCAN':1, 
        'CONTROL':2, 
        'USER_RAMP':3,
        'MAN_SETPOINT':4}
MonitorOut_dict = {'ERR_OPO':0,
            'ERR_SHG':1,
            'ERR_etalon':2,
            'PIEZO_OPO':4,
            'PIEZO_SHG':5,
            'PIEZO_etalon':6,
            'PIEZO_reference':7,
            'PUMP_power':9,
            'SHG_power':11,
            'OPO_power':12
            }
ScanningMode_dict = {'SAWTOOTH':0,
            'TRIANGLE':1}
RegMode = SimpleNamespace(**RegMode_dict)
MonitorOut = SimpleNamespace(**MonitorOut_dict)
ScanningMode = SimpleNamespace(**ScanningMode_dict)

def laser_is_connected(func):
    def wrapper(self, *arg, **kw):
        if self.cwstate == 1:
            res = func(self, *arg, **kw)
            return res
        else:
            pass#print("Cwave is not connected!")
    return wrapper

class CwaveLaser(Base):
    """ Lazor dummy

    Example config for copy-paste:

    laser_dummy:
        module.Class: 'laser.cwave_laser.CwaveLaser'
        cwave_ip: '192.168.202.52 :10001 '
        cwave_dll: './cwave/CWAVE_DLL.dll'
    """
    _cwave_ip = ConfigOption('cwave_ip', '192.168.202.52 :10001', missing='warn')
   
# self.status_keys = ['ready', 'OPOstepper', 'OPOtemp', 'SHGstepper', 'SHGtemp', 'Thin etalon', 'lockOPO', 'lockSHG', 'lockEtalon', 'laserEmission', 'refTemp']


    def __init__(self, **kwargs):
        """ """
        super().__init__(**kwargs)
        self.VoltRange = (0, 100)

        self.wavelength = 0


    def on_activate(self):
        """ Activate module.
        """
        this_dir = os.path.dirname(__file__)
        prev_dir = os.getcwd()
        os.chdir(this_dir)
        self.cwave_dll = CDLL("CWAVE_DLL.dll")
        os.chdir(prev_dir)
        self.cwstate = 0
        self.scanner_setpoint = 0
        self.shutters = {'laser_en':True,
                        'shtter_las': True, 
                        'shtter_shg':True, 
                        'shtter_las_out': True,  
                        'shtter_opo_out':True, 
                        'shtter_shg_out':True}
        self.status_cwave = {'laser':False,
                            'temp_ref':False,
                            'temp_opo': False,
                            'temp_shg':False,
                            'lock_opo':False,
                            'lock_shg':False,
                            'lock_etalon': False
                            }
        self._reg_modes = {'opo': RegMode.CONTROL,
                        'shg': RegMode.CONTROL,
                        'eta': RegMode.CONTROL}
        
        self.cwstate = 0

    def connect(self):
        """ Turn on laser.

            @return LaserState: actual laser state
        """
        self.cwstate = self.cwave_dll.cwave_connect(c_char_p(self._cwave_ip.encode('utf-8')))
        if self.cwstate != 1:
            raise Exception('Apparently cwave is connected somewhere else.')
        self.cwstate = 1
        return self.cwstate
    
    def disconnect(self):
        """ Turn on laser.
            @return LaserState: actual laser state
        """
        self.cwave_dll.cwave_disconnect()
        self.cwstate = 0
        return self.cwstate

    @laser_is_connected
    def scan(self, scan_duration, lowerlimit=0, upperlimit=99, scan_mode=ScanningMode.SAWTOOTH):
        scan_range = (1, 60000)
        if (scan_duration < scan_range[0]) or (scan_duration > scan_range[1]):
            print("duration should be > 1 less than 60000")
            return 0
        if abs(upperlimit - lowerlimit) < 10:
            print("delta should be >= 10")
            return  0
        if scan_duration < 1:
            print("Too short of duration. Must be larger, than 1")
        scan_on = self.set_regopo_mode(RegMode.USER_RAMP)
        if scan_on:
            scancw = self.cwave_dll.set_regopo_extramp(c_char_p(int(scan_duration)), c_char_p(int(scan_mode)), c_char_p(int(lowerlimit)), c_char_p(int(upperlimit)))
            self.select_monitor_out(MonitorOut.PIEZO_OPO)
            return scancw
    @laser_is_connected
    def get_wavelength(self):
        self.wavelength = int(self.get_int_value('opo_lambda')/100)
        return self.wavelength
    @laser_is_connected
    def set_regopo_mode(self, mode=RegMode.CONTROL):
        return self.set_int_value('regopo_on', mode)
    @laser_is_connected
    def set_regshg_mode(self, mode=RegMode.CONTROL):
        return self.set_int_value('regshg_on', mode)
    @laser_is_connected
    def get_laser_status(self): 
        for stat_name in self.status_cwave.keys():
            statbit = eval(f"self.cwave_dll.get_status_{stat_name}()")
            if stat_name == 'laser':
                self.status_cwave.update({stat_name: bool(statbit)})
            else:
                self.status_cwave.update({stat_name: not bool(statbit)})
        return self.status_cwave

    @laser_is_connected
    def get_power(self):
        """
        :return: int output power in mW: shg, opo, laser
        """
        shg = self.cwave_dll.get_photodiode_shg()
        opo = self.cwave_dll.get_photodiode_opo()
        laser = self.cwave_dll.get_photodiode_laser()
        return shg, opo, laser
    @laser_is_connected
    def select_monitor_out(self, value, monitor = 2):
        """
        value:
        0: Error Signal OPO
        1: Error Signal SHG
        2: Error Signal Etalon
        4: Piezo OPO
        5: Piezo SHG
        6: Piezo Etalon
        7: Piezo Reference
        9: Pump laser power
        11: SHG power
        12: OPO power
        """
        if monitor == 1:
            return self.set_int_value('monout_sel', value)
        elif monitor == 2:
            return self.set_int_value('monout2_sel', value)
    @laser_is_connected
    def get_shutters_states(self):
        """
        :param str shutter: 'las', 'shg', 'las_out', 'opo_out', 'shg_out'
        :return int: 1: open 0: close
        """
        for sh in self.shutters.keys():
            shstat = self.get_int_value(f'shtter{sh}')
            if shstat not in [0, 1]:
                shstat = self.shutters[sh]
            self.shutters.update({sh : shstat})
        return self.shutters
    @laser_is_connected
    def get_regmodes(self):
        """
        :return: 0: off, 1: scan, 2: control, 3: user ramp, 4: manual setpoint
        """
        opo = self.get_int_value('regopo_on')
        shg = self.get_int_value('regshg_on')
        eta = self.get_int_value('regeta_on')
        for p in ['opo', 'shg', 'eta']:
            stat = self.get_int_value(f'reg{p}_on')
            self._reg_modes.update({p:stat})
        return self._reg_modes
    
    @laser_is_connected 
    def set_regmode_control(self, param):
        self.set_int_value(f'reg{param}_on', RegMode.CONTROL)

    @laser_is_connected 
    def set_regmode_manual(self, param):
        self.set_int_value(f'reg{param}_on', RegMode.OFF)

    @laser_is_connected
    def set_command(self, cmd):
        return self.cwave_dll.set_command(f"{cmd}".encode('utf-8'))

    # def optimize_cwave(self, )
    @laser_is_connected
    def set_int_value(self, param, intval):
        return self.cwave_dll.set_intvalue(param.encode('utf-8'), c_char_p(int(intval)))

    
    def set_thick_etalon(self, pm):
        "move pm picometers"
        self.set_int_value('thicketa_rel_hr', pm)

    def set_wavelength(self, delta_lambda):
        self.set_int_value('opo_rlambda', delta_lambda)
 
    

    @laser_is_connected
    def get_int_value(self, param):
        return self.cwave_dll.get_intvalue(param.encode('utf-8'))

    def on_deactivate(self):
        """ Deactivate module.
        """
        if self.cwstate == 1:
            self.disconnect()
        print('C-WAVE disconnected')

    @laser_is_connected
    @QtCore.Slot()
    def set_shutters_states(self):
        for sh_key, sh_val in self.shutters.items():
            shstat = self.set_int_value(f'{sh_key}', sh_val)
            if shstat not in [0, 1]:
                shstat = self.shutters[sh_key]
            self.shutters.update({sh_key : sh_val})
        return self.shutters
    @laser_is_connected
    def read_photodiode_laser(self):
        return self.cwave_dll.get_photodiode_laser()
    @laser_is_connected
    def read_photodiode_opo(self):
        return self.cwave_dll.get_photodiode_opo()
    @laser_is_connected
    def read_photodiode_shg(self):
        return self.cwave_dll.get_photodiode_shg()