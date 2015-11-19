# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 11:53:49 2015

@author: s_ntomek
"""
import numpy as np

class SamplingFunctions():
    """ 
    Collection of mathematical functions used for sampling of the pulse sequences
    """
    def __init__(self):
        self.func_config = {'Idle': [], 'DC': ['amplitude'], 'Sin': ['frequency', 'amplitude', 'phase'], 'Cos': ['frequency', 'amplitude', 'phase']}
        self.func_config['DoubleSin'] = ['frequency1', 'frequency2', 'amplitude1', 'amplitude2', 'phase1', 'phase2']
        self.func_config['TripleSin'] = ['frequency1', 'frequency2', 'frequency3', 'amplitude1', 'amplitude2', 'amplitude3', 'phase1', 'phase2', 'phase3']
        self._math_function = {'Idle': self.__idle, 'DC': self.__dc, 'Sin': self.__sin, 'Cos': self.__cos}
        self._math_function['DoubleSin'] = self.__doublesin
        self._math_function['TripleSin'] = self.__triplesin
    
    def __idle(self, time_arr, parameters={}):
        result_arr = np.zeros(len(time_arr))
        return result_arr
        
    def __dc(self, time_arr, parameters):
        amp = parameters['amplitude']
        result_arr = np.full(len(time_arr), amp)
        return result_arr
    
    def __sin(self, time_arr, parameters):
        amp = parameters['amplitude']
        freq = parameters['frequency']
        phase = 180*np.pi * parameters['phase']
        result_arr = amp * np.sin(2*np.pi * freq * time_arr + phase)
        return result_arr
    
    def __cos(self, time_arr, parameters):
        amp = parameters['amplitude']
        freq = parameters['frequency']
        phase = 180*np.pi * parameters['phase']
        result_arr = amp * np.cos(2*np.pi * freq * time_arr + phase)
        return result_arr
    
    def __doublesin(self, time_arr, parameters):
        amp1 = parameters['amplitude1']
        amp2 = parameters['amplitude2']
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        phase1 = 180*np.pi * parameters['phase1']
        phase2 = 180*np.pi * parameters['phase2']
        result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1) 
        result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
        return result_arr
        
    def __triplesin(self, time_arr, parameters):
        amp1 = parameters['amplitude1']
        amp2 = parameters['amplitude2']
        amp3 = parameters['amplitude3']
        freq1 = parameters['frequency1']
        freq2 = parameters['frequency2']
        freq3 = parameters['frequency3']
        phase1 = 180*np.pi * parameters['phase1']
        phase2 = 180*np.pi * parameters['phase2']
        phase3 = 180*np.pi * parameters['phase3']
        result_arr = amp1 * np.sin(2*np.pi * freq1 * time_arr + phase1) 
        result_arr += amp2 * np.sin(2*np.pi * freq2 * time_arr + phase2)
        result_arr += amp3 * np.sin(2*np.pi * freq3 * time_arr + phase3)
        return result_arr
    
    
    
        
    