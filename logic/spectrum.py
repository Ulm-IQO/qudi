# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class that captures and processes fluorescence spectra.

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

from qtpy import QtCore
from collections import OrderedDict
import numpy as np
import matplotlib.pyplot as plt

from core.module import Connector, StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from logic.generic_logic import GenericLogic


class SpectrumLogic(GenericLogic):

    """This logic module gathers data from the spectrometer.
    """

    _modclass = 'spectrumlogic'
    _modtype = 'logic'

    # declare connectors
    spectrometer = Connector(interface='SpectrometerInterface')
    odmrlogic = Connector(interface='ODMRLogic')
    savelogic = Connector(interface='SaveLogic')

    # declare status variables
    _spectrum_data = StatusVar('spectrum_data', np.empty((2, 0)))
    _spectrum_background = StatusVar('spectrum_background', np.empty((2, 0)))
    _background_correction = StatusVar('background_correction', False)

    # declare signals
    sig_specdata_updated = QtCore.Signal()
    sig_next_diff_loop = QtCore.Signal()

    def __init__(self, **kwargs):
        """ Create SpectrometerLogic object with connectors.

          @param dict kwargs: optional parameters
        """
        super().__init__(**kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._spectrum_data_corrected = np.array([])
        self._calculate_corrected_spectrum()

        self.diff_spec_data_mod_on = np.array([])
        self.diff_spec_data_mod_off = np.array([])
        self.repetition_count = 0    # count loops for differential spectrum

        self._spectrometer_device = self.spectrometer()
        self._odmr_logic = self.odmrlogic()
        self._save_logic = self.savelogic()

        self.sig_next_diff_loop.connect(self._loop_differential_spectrum)
        self.sig_specdata_updated.emit()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            pass

    def get_single_spectrum(self, background=False):
        """ Record a single spectrum from the spectrometer.
        """
        if background:
            self._spectrum_background = netobtain(self._spectrometer_device.recordSpectrum())
        else:
            self._spectrum_data = netobtain(self._spectrometer_device.recordSpectrum())

        self._calculate_corrected_spectrum()

        # Clearing the differential spectra data arrays so that they do not get
        # saved with this single spectrum.
        self.diff_spec_data_mod_on = np.array([])
        self.diff_spec_data_mod_off = np.array([])

        self.sig_specdata_updated.emit()

    def _calculate_corrected_spectrum(self):
        self._spectrum_data_corrected = np.copy(self._spectrum_data)
        if len(self._spectrum_background) == 2 \
                and len(self._spectrum_background[1, :]) == len(self._spectrum_data[1, :]):
            self._spectrum_data_corrected[1, :] -= self._spectrum_background[1, :]
        else:
            self.log.warning('Background spectrum has a different dimension then the acquired spectrum. '
                             'Returning raw spectrum. '
                             'Try acquiring a new background spectrum.')

    @property
    def spectrum_data(self):
        if self._background_correction:
            self._calculate_corrected_spectrum()
            return self._spectrum_data_corrected
        else:
            return self._spectrum_data

    @property
    def background_correction(self):
        return self._background_correction

    @background_correction.setter
    def background_correction(self, correction=None):
        if correction is None or correction:
            self._background_correction = True
        else:
            self._background_correction = False
        self.sig_specdata_updated.emit()

    def save_raw_spectrometer_file(self, path='', postfix=''):
        """Ask the hardware device to save its own raw file.
        """
        # TODO: sanity check the passed parameters.

        self._spectrometer_device.saveSpectrum(path, postfix=postfix)

    def start_differential_spectrum(self):
        """Start a differential spectrum acquisition.  An initial spectrum is recorded to initialise the data arrays to the right size.
        """

        self._continue_differential = True

        # Taking a demo spectrum gives us the wavelength values and the length of the spectrum data.
        demo_data = netobtain(self._spectrometer_device.recordSpectrum())

        wavelengths = demo_data[0, :]
        empty_signal = np.zeros(len(wavelengths))

        # Using this information to initialise the differential spectrum data arrays.
        self._spectrum_data = np.array([wavelengths, empty_signal])
        self.diff_spec_data_mod_on = np.array([wavelengths, empty_signal])
        self.diff_spec_data_mod_off = np.array([wavelengths, empty_signal])
        self.repetition_count = 0

        # Starting the measurement loop
        self._loop_differential_spectrum()

    def resume_differential_spectrum(self):
        """Resume a differential spectrum acquisition.
        """

        self._continue_differential = True

        # Starting the measurement loop
        self._loop_differential_spectrum()

    def _loop_differential_spectrum(self):
        """ This loop toggles the modulation and iteratively records a differential spectrum.
        """

        # If the loop should not continue, then return immediately without
        # emitting any signal to repeat.
        if not self._continue_differential:
            return

        # Otherwise, we make a measurement and then emit a signal to repeat this loop.

        # Toggle on, take spectrum and add data to the mod_on data
        self.toggle_modulation(on=True)
        these_data = netobtain(self._spectrometer_device.recordSpectrum())
        self.diff_spec_data_mod_on[1, :] += these_data[1, :]

        # Toggle off, take spectrum and add data to the mod_off data
        self.toggle_modulation(on=False)
        these_data = netobtain(self._spectrometer_device.recordSpectrum())
        self.diff_spec_data_mod_off[1, :] += these_data[1, :]

        self.repetition_count += 1    # increment the loop count

        # Calculate the differential spectrum
        self._spectrum_data[1, :] = self.diff_spec_data_mod_on[
            1, :] - self.diff_spec_data_mod_off[1, :]

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
            self._odmr_logic.mw_cw_on()
        elif not on:
            self._odmr_logic.mw_off()
        else:
            print("Parameter 'on' needs to be boolean")

    def save_spectrum_data(self, background=False):
        """ Saves the current spectrum data to a file.
        """
        filepath = self._save_logic.get_path_for_module(module_name='spectra')
        if background:
            filelabel = 'background'
            spectrum_data = self._spectrum_background
        else:
            filelabel = 'spectrum'
            spectrum_data = self._spectrum_data

        # write experimental parameters
        parameters = OrderedDict()
        parameters['Spectrometer acquisition repetitions'] = self.repetition_count

        # prepare the data in an OrderedDict:
        data = OrderedDict()

        data['wavelength'] = spectrum_data[0, :]

        # If the differential spectra arrays are not empty, save them as raw data
        if len(self.diff_spec_data_mod_on) != 0 and len(self.diff_spec_data_mod_off) != 0:
            data['signal_mod_on'] = self.diff_spec_data_mod_on[1, :]
            data['signal_mod_off'] = self.diff_spec_data_mod_off[1, :]
            data['differential'] = spectrum_data[1, :]
        else:
            data['signal'] = spectrum_data[1, :]

        if not background and len(self._spectrum_data_corrected) != 0:
            data['corrected'] = self._spectrum_data_corrected[1, :]

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)

        fig, ax1 = plt.subplots()

        ax1.plot(data['wavelength'], data['signal'])

        ax1.set_xlabel('Wavelength (nm)')
        ax1.set_ylabel('Signal (arb. u.)')

        fig.tight_layout()

        # Save to file
        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   plotfig=fig)
        self.log.debug('Spectrum saved to:\n{0}'.format(filepath))
