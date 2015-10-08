# -*- coding: utf-8 -*-
"""
This file contains the QuDi couner logic class.

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Kay D. Jahnke
Copyright (C) 2015 Alexander Stark
Copyright (C) 2015 Jan M. Binder
"""

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict
import numpy as np
import time
import datetime


class SpectrumLogic(GenericLogic):
    """This logic module gathers data from the spectrometer.
    """

    sig_specdata_updated = QtCore.Signal()
    sig_next_diff_loop = QtCore.Signal()

    _modclass = 'spectrumlogic'
    _modtype = 'logic'

    ## declare connectors
    _in = { 'spectrometer': 'SpectrometerInterface',
            'odmrlogic1' : 'ODMRLogic',
            'savelogic': 'SaveLogic'
            }
    _out = {'spectrumlogic': 'SpectrumLogic'}

    def __init__(self, manager, name, config, **kwargs):
        """ Create SpectrometerLogic object with connectors.

          @param object manager: Manager object that loaded this module
          @param str name: unique module name
          @param dict config: module configuration
          @param dict kwargs: optional parameters
        """
        ## declare actions for state transitions
        state_actions = {'onactivate': self.activation, 'ondeactivate': self.deactivation}
        super().__init__(manager, name, config, state_actions, **kwargs)

        #locking for thread safety
        self.threadlock = Mutex()



    def activation(self, e):
        """ Initialisation performed during activation of the module.

          @param object e: Fysom state change event
        """
        self.spectrum_data = np.array([])
        self.diff_spec_data_mod_on = np.array([])
        self.diff_spec_data_mod_off = np.array([])

        self._spectrometer_device = self.connector['in']['spectrometer']['object']
        self._odmr_logic = self.connector['in']['odmrlogic1']['object']
        self._save_logic = self.connector['in']['savelogic']['object']
        
        self.sig_next_diff_loop.connect(self._loop_differential_spectrum)


    def deactivation(self, e):
        """ Deinitialisation performed during deactivation of the module.

          @param object e: Fysom state change event
        """
        if self.getState() != 'idle' and self.getState() != 'deactivated':
            pass
        

    def get_single_spectrum(self):
        self.spectrum_data = self._spectrometer_device.recordSpectrum()

        # Clearing the differential spectra data arrays so that they do not get saved with this single spectrum.
        self.diff_spec_data_mod_on = np.array([])
        self.diff_spec_data_mod_off = np.array([])


        self.sig_specdata_updated.emit()

    def save_raw_spectrometer_file(self, path = '', postfix = '' ):
        """Ask the hardware device to save its own raw file.
        """
        #TODO: sanity check the passed parameters.

        self._spectrometer_device.saveSpectrum( path, postfix = postfix )


    def start_differential_spectrum(self):
        """Start a differential spectrum acquisition.  An initial spectrum is recorded to initialise the data arrays to the right size.
        """

        self._continue_differential = True

        # Taking a demo spectrum gives us the wavelength values and the length of the spectrum data.
        demo_data = self._spectrometer_device.recordSpectrum()

        wavelengths = demo_data[0,:]
        empty_signal = np.zeros(len(wavelengths) )

        # Using this information to initialise the differential spectrum data arrays.
        self.spectrum_data = np.array( [wavelengths, empty_signal] )
        self.diff_spec_data_mod_on = np.array( [wavelengths, empty_signal] )
        self.diff_spec_data_mod_off= np.array( [wavelengths, empty_signal] )

        # Starting the measurement loop
        self._loop_differential_spectrum()

    def _loop_differential_spectrum(self):
        """ This loop toggles the modulation and iteratively records a differential spectrum.
        """
        
        # If the loop should not continue, then return immediately without emitting any signal to repeat.
        if not self._continue_differential:
            return

        # Otherwise, we make a measurement and then emit a signal to repeat this loop.
        
        # Toggle on, take spectrum and add data to the mod_on data
        self.toggle_modulation( on=True )
        these_data = self._spectrometer_device.recordSpectrum()
        self.diff_spec_data_mod_on[1,:] += these_data[1,:]

        # Toggle off, take spectrum and add data to the mod_off data
        self.toggle_modulation( on=False )
        these_data = self._spectrometer_device.recordSpectrum()
        self.diff_spec_data_mod_off[1,:] += these_data[1,:]

        # Calculate the differential spectrum
        self.spectrum_data[1,:] = self.diff_spec_data_mod_on[1,:] - self.diff_spec_data_mod_off[1,:]

        self.sig_specdata_updated.emit()

        self.sig_next_diff_loop.emit()


    def stop_differential_spectrum(self):
        """Stop an ongoing differential spectrum acquisition
        """
        
        self._continue_differential = False

    def toggle_modulation(self, on):
        """ Toggle the modulation.
        """

        if on:
            self._odmr_logic.MW_on()
        elif not on:
            self._odmr_logic.MW_off()
        else:
            print("Parameter 'on' needs to be boolean")

    def save_spectrum_data(self):
        """ Saves the current spectrum data to a file.
        """
        filepath = self._save_logic.get_path_for_module(module_name='spectra')
        filelabel = 'spectrum'
        timestamp = datetime.datetime.now()

        # prepare the data in an OrderedDict:
        data = OrderedDict()

        data['wavelength'] = self.spectrum_data[0,:]
        data['signal'] = self.spectrum_data[1,:]

        self._save_logic.save_data( data, filepath, 
                                    filelabel=filelabel, timestamp=timestamp,
                                    as_text=True)

        #If the differential spectra arrays are not empty, save them as raw data
        if len(self.diff_spec_data_mod_on) != 0 and len(self.diff_spec_data_mod_off) !=0:
            filelabel = 'spectrum_raw_modulation'
            data = OrderedDict()

            data['wavelength'] = self.diff_spec_data_mod_on[0,:]
            data['signal_mod_on'] = self.diff_spec_data_mod_on[1,:]
            data['signal_mod_off'] = self.diff_spec_data_mod_off[1,:]

            self._save_logic.save_data( data, filepath, 
                                        filelabel=filelabel, timestamp=timestamp,
                                        as_text=True)
