# -*- coding: utf-8 -*-
"""
This file contains Qudi methods for handling real-world values with units.

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

import numpy as np
from scipy import signal
try:
    import pyqtgraph.functions as fn
except:
    fn = None
import math


def get_unit_prefix_dict():
    """ Return the dictionary, which assigns the prefix of a unit to its
        proper order of magnitude.
    @return dict: keys are string prefix and items are magnitude values.
    """

    unit_prefix_dict = {
        'y': 1e-24,
        'z': 1e-21,
        'a': 1e-18,
        'f': 1e-15,
        'p': 1e-12,
        'n': 1e-9,
        'µ': 1e-6,
        'm': 1e-3,
        '': 1,
        'k': 1e3,
        'M': 1e6,
        'G': 1e9,
        'T': 1e12,
        'P': 1e15,
        'E': 1e18,
        'Z': 1e21,
        'Y': 1e24
    }
    return unit_prefix_dict


class ScaledFloat(float):
    """
    Format code 'r' for scaled output.

    Examples
    --------
    >>> '{:.0r}A'.format(ScaledFloat(50))
    50 A
    >>> '{:.1r}A'.format(ScaledFloat(1.5e3))
    1.5 kA
    >>> '{:.1r}A'.format(ScaledFloat(2e-3))
    2.0 mA
    >>> '{:rg}A'.format(ScaledFloat(2e-3))
    2 mA
    >>> '{:rf}A'.format(ScaledFloat(2e-3))
    2.000000 mA
    """

    @property
    def scale(self):
        """
        Returns the scale. (No prefix if 0)

        Examples
        --------
        1e-3: m
        1e6: M
        """

        # Zero makes the log crash and should not have a prefix
        if self == 0:
            return ''

        exponent = math.floor(math.log10(abs(self)) / 3)
        if exponent < -8:
            exponent = -8
        if exponent > 8:
            exponent = 8
        prefix = 'yzafpnµm kMGTPEZY'
        return prefix[8 + exponent].strip()

    @property
    def scale_val(self):
        """ Returns the scale value which can be used to devide the actual value

        Examples
        --------
        m: 1e-3
        M: 1e6
        """
        scale_str = self.scale
        return get_unit_prefix_dict()[scale_str]

    def __format__(self, fmt):
        """
        Fromats the string using format fmt.

        r for scaled output.

        Parameters
        ----------
        fmt : str format string
        """
        autoscale = False
        if (len(fmt) >= 2):
            if fmt[-2] == 'r':
                autoscale = True
                fmt = fmt[:-2] + fmt[-1]
            elif fmt[-1] == 'r':
                autoscale = True
                fmt = fmt[:-1] + 'f'
        elif fmt[-1] == 'r':
            autoscale = True
            fmt = fmt[:-1] + 'f'
        if (autoscale):
            scale = self.scale
            if (scale == 'u'):
                index = 'micro'
            else:
                index = scale
            value = self / get_unit_prefix_dict()[index]
            return '{:s} {:s}'.format(value.__format__(fmt), scale)
        else:
            return super().__format__(fmt)


def create_formatted_output(param_dict, num_sig_digits=5):
    """ Display a parameter set nicely in SI units.

    @param dict param_dict: dictionary with entries being again dictionaries
                       with two needed keywords 'value' and 'unit' and one
                       optional keyword 'error'. Add the proper items to the
                       specified keywords.
                       Note, that if no error is specified, no proper
                       rounding (and therefore displaying) can be
                       guaranteed.

    @param int num_sig_digits: optional, the number of significant digits will
                               be taken, if the rounding procedure was not
                               successful at all. That will ensure at least that
                               not all the digits are displayed.
                               According to that the error will be displayed.

    @return str: a string, which is nicely formatted.

    Note:  If you want that the values are displayed in a certain order, then
           use OrderedDict from the collections package.
    Note2: The absolute tolerance to a zero is set to 1e-18.

    Example of a param dict:
        param_dict = {'Rabi frequency': {'value':123.43,   'error': 0.321,  'unit': 'Hz'},
                      'ODMR contrast':  {'value':2.563423, 'error': 0.523,  'unit': '%'},
                      'Fidelity':       {'value':0.783,    'error': 0.2222, 'unit': ''}}

        If you want to access on the value of the Fidelity, then you can do
        that via:
            param_dict['Fidelity']['value']
        or on the error of the ODMR contrast:
            param_dict['ODMR contrast']['error']


    """
    if (fn is None):
        raise Exception('This function requires pyqtgraph.')

    output_str = ''
    atol = 1e-18    # absolute tolerance for the detection of zero.

    for entry in param_dict:
        if param_dict[entry].get('error') is not None:

            value, error, digit = round_value_to_error(
                param_dict[entry]['value'], param_dict[entry]['error'])

            if (np.isclose(value, 0.0, atol=atol)
                    or np.isnan(error)
                    or np.isclose(error, 0.0, atol=atol)
                    or np.isinf(error)):
                sc_fact, unit_prefix = fn.siScale(param_dict[entry]['value'])
                str_val = '{0:.{1}e}'.format(
                    param_dict[entry]['value'], num_sig_digits - 1)
                if np.isnan(np.float(str_val)):
                    value = np.NAN
                elif np.isinf(np.float(str_val)):
                    value = np.inf
                else:
                    value = float('{0:.{1}e}'.format(
                        param_dict[entry]['value'], num_sig_digits - 1))

            else:
                # the factor 10 moves the displayed digit by one to the right,
                # so that the values from 100 to 0.1 are displayed within one
                # range, rather then from the value 1000 to 1, which is
                # default.
                sc_fact, unit_prefix = fn.siScale(error * 10)

            output_str += '{0}: {1} \u00B1 {2} {3}{4} \n'.format(entry,
                                                                 round(
                                                                     value * sc_fact, num_sig_digits - 1),
                                                                 round(
                                                                     error * sc_fact, num_sig_digits - 1),
                                                                 unit_prefix,
                                                                 param_dict[entry][
                                                                     'unit'],
                                                                 )

        else:
            output_str += '{0}: '.format(entry) + fn.siFormat(param_dict[entry]['value'],
                                                              precision=num_sig_digits,
                                                              suffix=param_dict[entry]['unit']) + '\n'

    return output_str


def round_value_to_error(value, error):
    """ The scientifically correct way of rounding a value according to an error.

    @param float or int value: the measurement value
    @param float or int error: the error for that measurement value

    @return tuple(float, float, int):
                float value: the rounded value according to the error
                float error: the rounded error
                int rounding_digit: the digit, to which the rounding
                                    procedure was performed. Note a positive
                                    number indicates the position of the
                                    digit right from the comma, zero means
                                    the first digit left from the comma and
                                    negative numbers are the digits left
                                    from the comma. That is a convention
                                    which is used in the native round method
                                    and the method numpy.round.

    Note1: the input type of value or error will not be changed! If float is
           the input, float will be the output, same applies to integer.

    Note2: This method is not returning strings, since each display method
           might want to display the rounded values in a different way.
           (in exponential representation, in a different magnitude, ect.).

    Note3: This function can handle an invalid error, i.e. if the error is
           zero, NAN or infinite. The absolute tolerance to detect a number as
           zero is set to 1e-18.

    Procedure explanation:
    The scientific way of displaying a measurement result in the presents of
    an error is applied here. It is the following procedure:
        Take the first leading non-zero number in the error value and check,
        whether the number is a digit within 3 to 9. Then the rounding value
        is the specified digit. Otherwise, if first leading digit is 1 or 2
        then the next right digit is the rounding value.
        The error is rounded according to that digit and the same applies
        for the value.

    Example 1:
        x_meas = 2.05650234, delta_x = 0.0634
            => x =  2.06 +- 0.06,   (output: (2.06, 0.06, 2)    )

    Example 2:
        x_meas = 0.34545, delta_x = 0.19145
            => x = 0.35 +- 0.19     (output: (0.35, 0.19, 2)    )

    Example 3:
        x_meas = 239579.23, delta_x = 1289.234
            => x = 239600 +- 1300   (output: (239600.0, 1300.0, -2) )

    Example 4:
        x_meas = 961453, delta_x = 3789
            => x = 961000 +- 4000   (output: (961000, 4000, -3) )

    """

    atol = 1e-18    # absolute tolerance for the detection of zero.

    # check if error is zero, since that is an invalid input!
    if np.isclose(error, 0.0, atol=atol) or np.isnan(error) or np.isinf(error):
        #self.log.error('Cannot round to the error, since either a zero error ')
        # logger.warning('Cannot round to the error, since either a zero error '
        #            'value was passed for the number {0}, or the error is '
        #            'NaN: Error value: {1}. '.format(value, error))

        # set the round digit to float precision
        round_digit = -12

        return value, error, round_digit

    # error can only be positive!
    log_val = np.log10(abs(error))

    if log_val < 0:
        round_digit = -(int(log_val) - 1)
    else:
        round_digit = -(int(log_val))

    first_err_digit = '{:e}'.format(error)[0]

    if first_err_digit in ('1', '2'):
        round_digit += 1

    # Use the python round function, since np.round uses the __repr__ conversion
    # function which shows enough digits to unambiguously identify the number.
    # But the __str__ conversion should round the number to a reasonable number
    # of digits, which is the standard output of the python round function.
    # Therefore take the python round function.

    return round(value, round_digit), round(error, round_digit), round_digit


def get_relevant_digit(entry):
    """ By using log10, abs and int operations, the proper relevant digit is
        obtained.

    @param flaot entry:

    @return: int, the leading relevant exponent
    """

    # the log10 can only be calculated of a positive number.
    entry = np.abs(entry)

    # the log of zero crashes, so return 0
    if entry == 0:
        return 0

    if np.log10(entry) >= 0:
        return int(np.log10(entry))
    else:
        # catch the asymmetric behaviour of the log and int operation.
        return int(int(np.abs(np.log10(entry))) + 1 + np.log10(entry)) - (int(np.abs(np.log10(entry))) + 1)


def get_si_norm(entry):
    """ A rather different way to display the value in SI notation.

    @param float entry: the float number from which normalization factor should
                        be obtained.

    @return: norm_val, normalization
            float norm_val: the value in a normalized representation.
            float normalization: the factor with which to divide the number.
    """
    val = get_relevant_digit(entry)
    fact = int(val / 3)
    power = int(3 * fact)
    norm = 10**(power)

    return entry / norm, norm


def is_number(test_value):
    """ Check whether passed value is a number

    @return: bool, True if the passed value is a number, otherwise false.
    """
    return is_integer(test_value) or is_float(test_value) or is_complex(test_value)


def is_integer(test_value):
    """ Check all available integer representations.

    @return: bool, True if the passed value is a integer, otherwise false.
    """

    return type(test_value) in [np.int, np.int8, np.int16, np.int32, np.int64,
                                np.uint, np.uint8, np.uint16, np.uint32,
                                np.uint64]


def is_float(test_value):
    """ Check all available float representations.

    @return: bool, True if the passed value is a float, otherwise false.
    """
    return type(test_value) in [np.float, np.float16, np.float32, np.float64]


def is_complex(test_value):
    """ Check all available complex representations.

    @return: bool, True if the passed value is a complex value, otherwise false.
    """

    return type(test_value) in [np.complex, np.complex64, np.complex128]


def in_range(value, lower_limit, upper_limit):
    """ Check if a value is in a given range an return closest possible value in range.
    Also check the range.

    @param value: value to be checked
    @param lower_limit: lowest allowed value
    @param upper_limit: highest allowed value
    @return: value closest to value in range
    """
    if upper_limit > lower_limit:
        u_limit = upper_limit
        l_limit = lower_limit
    else:
        l_limit = upper_limit
        u_limit = lower_limit

    if value > u_limit:
        return upper_limit
    if value < l_limit:
        return lower_limit
    return value


def get_ft_windows():
    """ Retrieve the available windows to be applied on signal data before FT.

    @return: dict with keys being the window name and items being again a dict
             containing the actual function and the normalization factor to
             calculate correctly the amplitude spectrum in the Fourier Transform

    To find out the amplitude normalization factor check either the scipy
    implementation on
        https://github.com/scipy/scipy/blob/v0.15.1/scipy/signal/windows.py#L336
    or just perform a sum of the window (oscillating parts of the window should
    be averaged out and constant offset factor will remain):
        MM=1000000  # choose a big number
        print(sum(signal.hanning(MM))/MM)
    """

    win = {'none': {'func': np.ones, 'ampl_norm': 1.0},
           'hamming': {'func': signal.hamming, 'ampl_norm': 1.0/0.54},
           'hann': {'func': signal.hann, 'ampl_norm': 1.0/0.5},
           'blackman': {'func': signal.blackman, 'ampl_norm': 1.0/0.42},
           'triang': {'func': signal.triang, 'ampl_norm': 1.0/0.5},
           'flattop': {'func': signal.flattop, 'ampl_norm': 1.0/0.2156},
           'bartlett': {'func': signal.bartlett, 'ampl_norm': 1.0/0.5},
           'parzen': {'func': signal.parzen, 'ampl_norm': 1.0/0.375},
           'bohman': {'func': signal.bohman, 'ampl_norm': 1.0/0.4052847},
           'blackmanharris': {'func': signal.blackmanharris, 'ampl_norm': 1.0/0.35875},
           'nuttall': {'func': signal.nuttall, 'ampl_norm': 1.0/0.3635819},
           'barthann': {'func': signal.barthann, 'ampl_norm': 1.0/0.5}}
    return win

def compute_ft(x_val, y_val, zeropad_num=0, window='none', base_corr=True,
               psd=False):
    """ Compute the Discrete fourier Transform of the power spectral density

    @param numpy.array x_val: 1D array
    @param numpy.array y_val: 1D array of same size as x_val
    @param int zeropad_num: optional, zeropadding (adding zeros to the end of
                            the array). zeropad_num >= 0, the size of the array
                            which is add to the end of the y_val before
                            performing the Fourier Transform (FT). The
                            resulting array will have the length
                                (len(y_val)/2)*(zeropad_num+1)
                            Note that zeropadding will not change or add more
                            information to the dft, it will solely interpolate
                            between the dft_y values (corresponds to a Sinc
                            interpolation method).
                            Set zeropad_num=1 to obtain output arrays which
                            have the same size as the input arrays.
                            Default is zeropad_num=0.
    @param str window: optional, the window function which should be applied to
                       the y values before Fourier Transform is calculated.
    @param bool base_corr: Select whether baseline correction shoud be performed
                           before calculating the FT.
    @param bool psd: optional, select whether the Discrete Fourier Transform or
                     the Power Spectral Density (PSD, which is just the FT of
                     the absolute square of the y-values) should be computed.
                     Default is psd=False.

    @return: tuple(dft_x, dft_y):
                be aware that the return arrays' length depend on the zeropad
                number like
                    len(dft_x) = len(dft_y) = (len(y_val)/2)*(zeropad_num+1)

    Pay attention that the return values of the FT have only half of the
    entries compared to the used signal input (if zeropad=0).

    In general, a window function should be applied on the y data before
    calculating the FT, to reduce spectral leakage. The Hann window for
    instance is almost never a bad choice. Use it like window='hann'

    Keep always in mind the relation to the Fourier transform space:
        T = delta_t * N_samples
    where delta_t is the distance between the time points and N_samples are the
    amount of points in the time domain. Consequently the sample rate is
        f_samplerate = T / N_samples

    Keep also in mind that the FT returns value from 0 to f_samplerate, or
        equivalently -f_samplerate/2 to f_samplerate/2.

    Difference between PSD and DFT:
    The power spectral density (PSD) describes how the power of your signal is
    distributed over frequency whilst the DFT shows the spectral content of
    your signal, i.e. the amplitude and phase of harmonics in your signal.
    """

    avail_windows = get_ft_windows()

    x_val = np.array(x_val)
    y_val = np.array(y_val)

    # Make a baseline correction to avoid a constant offset near zero
    # frequencies. Offset of the y_val from mean corresponds to half the value
    # at fft_y[0].
    corrected_y = y_val
    if base_corr:
        corrected_y = y_val - y_val.mean()

    ampl_norm_fact = 1.0
    # apply window to data to account for spectral leakage:
    if window in avail_windows:
        window_val = avail_windows[window]['func'](len(y_val))
        corrected_y = corrected_y * window_val
        # to get the correct amplitude in the amplitude spectrum
        ampl_norm_fact = avail_windows[window]['ampl_norm']

    # zeropad for sinc interpolation:
    zeropad_arr = np.zeros(len(corrected_y)*(zeropad_num+1))
    zeropad_arr[:len(corrected_y)] = corrected_y

    # Get the amplitude values from the fourier transformed y values.
    fft_y = np.abs(np.fft.fft(zeropad_arr))

    # Power spectral density (PSD) or just amplitude spectrum of fourier signal:
    pow = 1.0
    if psd:
        pow = 2.0

    # The factor 2 accounts for the fact that just the half of the spectrum was
    # taken. The ampl_norm_fact is the normalization factor due to the applied
    # window function (the offset value in the window function):
    fft_y = ((2/len(y_val)) * fft_y * ampl_norm_fact)**pow

    # Due to the sampling theorem you can only identify frequencies at half
    # of the sample rate, therefore the FT contains an almost symmetric
    # spectrum (the asymmetry results from aliasing effects). Therefore take
    # the half of the values for the display.
    middle = int((len(zeropad_arr)+1)//2)

    # sample spacing of x_axis, if x is a time axis than it corresponds to a
    # timestep:
    x_spacing = np.round(x_val[-1] - x_val[-2], 12)

    # use the helper function of numpy to calculate the x_values for the
    # fourier space. That function will handle an occuring devision by 0:
    fft_x = np.fft.fftfreq(len(zeropad_arr), d=x_spacing)

    return abs(fft_x[:middle]), fft_y[:middle]
