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
from time import sleep
from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from core.util.network import netobtain
from logic.generic_logic import GenericLogic

def automatic_flip(func):
    def wrapper(self, *arg, **kw):
        if self._automatic_flip:
            self._ello_flipper.move_forward()
            res = func(self, *arg, **kw)
            self._ello_flipper.home()
        else:
            res = func(self, *arg, **kw)
        return res
    return wrapper

class SpectrumLogic(GenericLogic):

    """This logic module gathers data from the spectrometer.

    Demo config:

    spectrumlogic:
        module.Class: 'spectrum.SpectrumLogic'
        connect:
            spectrometer: 'myspectrometer'
            savelogic: 'savelogic'
            odmrlogic: 'odmrlogic' # optional
            fitlogic: 'fitlogic'
    """

    # declare connectors
    spectrometer = Connector(interface='SpectrometerInterface')
    odmrlogic = Connector(interface='ODMRLogic', optional=True)
    savelogic = Connector(interface='SaveLogic')
    fitlogic = Connector(interface='FitLogic')
    nicard = Connector(interface='NationalInstrumentsXSeries')
    ello_devices = Connector(interface='ThorlabsElloDevices')
    # cwavelaser = Connector(interface='CwaveLaser')

    # declare status variables
    _automatic_flip = False
    _spectrum_data = StatusVar('spectrum_data', np.empty((2, 0)))
    _spectrum_background = StatusVar('spectrum_background', np.empty((2, 0)))
    _background_correction = StatusVar('background_correction', False)
    fc = StatusVar('fits', None)
    plot_domain = (450, 900)
    # Internal signals
    sig_specdata_updated = QtCore.Signal()
    sig_next_diff_loop = QtCore.Signal()
    # sig_cwave_shutter = QtCore.Signal()
    # External signals eg for GUI module
    spectrum_fit_updated_Signal = QtCore.Signal(np.ndarray, dict, str)
    fit_domain_updated_Signal = QtCore.Signal(np.ndarray)

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
       
        self.spectrum_fit = np.array([])
        self.fit_domain = np.array([])

        self.diff_spec_data_mod_on = np.array([])
        self.diff_spec_data_mod_off = np.array([])
        self.repetition_count = 0    # count loops for differential spectrum

        self._spectrometer_device = self.spectrometer()
        self.integration_time = self._spectrometer_device._integration_time
        self._odmr_logic = self.odmrlogic()
        self._save_logic = self.savelogic()
        self._ello_flipper = self.ello_devices().ello_flip
        # self._cwave = self.cwavelaser()
        # self.sig_cwave_shutter.connect(self._cwave.set_shutters_states)
        self._nicard = self.nicard()

        self.sig_next_diff_loop.connect(self._loop_differential_spectrum)
        self.sig_specdata_updated.emit()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() != 'idle' and self.module_state() != 'deactivated':
            pass

    @fc.constructor
    def sv_set_fits(self, val):
        """ Set up fit container """
        fc = self.fitlogic().make_fit_container('ODMR sum', '1d')
        fc.set_units(['m', 'c/s'])
        if isinstance(val, dict) and len(val) > 0:
            fc.load_from_dict(val)
        else:
            d1 = OrderedDict()
            d1['Gaussian peak'] = {
                'fit_function': 'gaussian',
                'estimator': 'peak'
                }
            default_fits = OrderedDict()
            default_fits['1d'] = d1
            fc.load_from_dict(default_fits)
        return fc

    @fc.representer
    def sv_get_fits(self, val):
        """ save configured fits """
        if len(val.fit_list) > 0:
            return val.save_to_dict()
        else:
            return None

    def flip_mirror(self, mode = True):
	    self._nicard.digital_channel_switch(self._nicard._flip_mirror_channel, mode=mode)

    @automatic_flip
    def get_single_spectrum(self, background=False):
        """ Record a single spectrum from the spectrometer.
        """
        self.fc.clear_result()
        # clear spectro,eter buffer
        self._spectrometer_device.clearBuffer()
        # sleep(self._spectrometer_device._integration_time)
        if background:
            self._spectrum_background = self._spectrometer_device.recordSpectrum()
        else:
            self._spectrum_data = self._spectrometer_device.recordSpectrum()
        
        lam, spec = self._spectrum_data[0, :], self._spectrum_data[1, :]
        plot_range = (lam > self.plot_domain[0]) * (lam < self.plot_domain[1])
        self._spectrum_data = self._spectrum_data[plot_range]

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

    def update_integration_time(self, integration_time):
        self._spectrometer_device._integration_time = integration_time
        self._spectrometer_device.setExposure(self._spectrometer_device._integration_time)


    def stop_differential_spectrum(self):
        """Stop an ongoing differential spectrum acquisition
        """

        self._continue_differential = False

    def toggle_modulation(self, on):
        """ Toggle the modulation.
        """
        if self._odmr_logic is None:
            return
        if on:
            self._odmr_logic.mw_cw_on()
        elif not on:
            self._odmr_logic.mw_off()
        else:
            print("Parameter 'on' needs to be boolean")

    def save_spectrum_data(self, background=False, name_tag='', custom_header = None):
        """ Saves the current spectrum data to a file.

        @param bool background: Whether this is a background spectrum (dark field) or not.

        @param string name_tag: postfix name tag for saved filename.

        @param OrderedDict custom_header:
            This ordered dictionary is added to the default data file header. It allows arbitrary
            additional experimental information to be included in the saved data file header.
        """
        filepath = self._save_logic.get_path_for_module(module_name='spectra')
        if background:
            filelabel = 'background'
            spectrum_data = self._spectrum_background
        else:
            filelabel = 'spectrum'
            spectrum_data = self._spectrum_data

        # Add name_tag as postfix to filename
        if name_tag != '':
            filelabel = filelabel + '_' + name_tag

        # write experimental parameters
        parameters = OrderedDict()
        parameters['Spectrometer acquisition repetitions'] = self.repetition_count

        # add all fit parameter to the saved data:
        if self.fc.current_fit_result is not None:
            parameters['Fit function'] = self.fc.current_fit

            for name, param in self.fc.current_fit_param.items():
                parameters[name] = str(param)
        
        # add any custom header params
        if custom_header is not None:
            for key in custom_header:
                parameters[key] = custom_header[key]

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

        fig = self.draw_figure()

        # Save to file
        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   plotfig=fig)
        self.log.debug('Spectrum saved to:\n{0}'.format(filepath))

    def draw_figure(self):
        """ Draw the summary plot to save with the data.

        @return fig fig: a matplotlib figure object to be saved to file.
        """
        wavelength = self.spectrum_data[0, :] # convert m to nm for plot
        spec_data = self.spectrum_data[1, :]

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0
        rescale_factor = 1
        
        # Rescale spectrum data with SI prefix
        while np.max(spec_data) / rescale_factor > 1000:
            rescale_factor = rescale_factor * 1000
            prefix_index = prefix_index + 1

        intensity_prefix = prefix[prefix_index]

        # Prepare the figure to save as a "data thumbnail"
        plt.style.use(self._save_logic.mpl_qd_style)

        fig, ax1 = plt.subplots()

        ax1.plot(wavelength,
                 spec_data / rescale_factor,
                 linestyle='-')
                #  linewidth=1
                # )
        # ax1.grid('--', )
        # If there is a fit, plot it also
        if self.fc.current_fit_result is not None:
            ax1.plot(self.spectrum_fit[0],  # convert m to nm for plot
                     self.spectrum_fit[1] / rescale_factor,
                     marker='None'
                    )

        ax1.set_xlabel('Wavelength (nm)')
        ax1.set_ylabel('Intensity ({}count)'.format(intensity_prefix))

        fig.tight_layout()

        return fig

    ################
    # Fitting things

    def get_fit_functions(self):
        """ Return the hardware constraints/limits
        @return list(str): list of fit function names
        """
        return list(self.fc.fit_list)

    def do_fit(self, fit_function=None, x_data=None, y_data=None):
        """
        Execute the currently configured fit on the measurement data. Optionally on passed data

        @param string fit_function: The name of one of the defined fit functions.

        @param array x_data: wavelength data for spectrum.

        @param array y_data: intensity data for spectrum.
        """
        if (x_data is None) or (y_data is None):
            x_data = self.spectrum_data[0]
            y_data = self.spectrum_data[1]
            if self.fit_domain.any():
                start_idx = self._find_nearest_idx(x_data, self.fit_domain[0])
                stop_idx = self._find_nearest_idx(x_data, self.fit_domain[1])

                x_data = x_data[start_idx:stop_idx]
                y_data = y_data[start_idx:stop_idx]

        if fit_function is not None and isinstance(fit_function, str):
            if fit_function in self.get_fit_functions():
                self.fc.set_current_fit(fit_function)
            else:
                self.fc.set_current_fit('No Fit')
                if fit_function != 'No Fit':
                    self.log.warning('Fit function "{0}" not available in Spectrum logic '
                                     'fit container.'.format(fit_function)
                                     )

        spectrum_fit_x, spectrum_fit_y, result = self.fc.do_fit(x_data, y_data)

        self.spectrum_fit = np.array([spectrum_fit_x, spectrum_fit_y])

        if result is None:
            result_str_dict = {}
        else:
            result_str_dict = result.result_str_dict
        self.spectrum_fit_updated_Signal.emit(self.spectrum_fit,
                                              result_str_dict,
                                              self.fc.current_fit
                                              )
        return

    def _find_nearest_idx(self, array, value):
        """ Find array index of element nearest to given value

        @param list array: array to be searched.
        @param float value: desired value.

        @return index of nearest element.
        """

        idx = (np.abs(array-value)).argmin()
        return idx

    def set_fit_domain(self, domain=None):
        """ Set the fit domain to a user specified portion of the data.

        If no domain is given, then this method sets the fit domain to match the full data domain.

        @param np.array domain: two-element array containing min and max of domain.
        """
        if domain is not None:
            self.fit_domain = domain
        else:
            self.fit_domain = np.array([self.spectrum_data[0, 0], self.spectrum_data[0, -1]])

        self.fit_domain_updated_Signal.emit(self.fit_domain)