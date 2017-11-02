# -*- coding: utf-8 -*-
"""
This file contains the QuDi FitLogic class, which provides all
fitting methods imported from the files in logic/fitmethods.

The fit_logic methods can be imported in any python code by using
the folling lines:

import sys
path_of_qudi = "<custom path>/qudi/"
sys.path.append(path_of_qudi)
from tools.fit_logic_standalone import FitLogic
fitting = FitLogic(path_of_qudi)



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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""


import logging
logger = logging.getLogger(__name__)

import numpy as np
import sys
from scipy.interpolate import InterpolatedUnivariateSpline
from lmfit import Parameters, models
import matplotlib.pylab as plt
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import importlib
from os import listdir,getcwd
from os.path import isfile, join
import os

#from scipy import special
#from scipy.special import gammaln as gamln
#import statsmodels.api as sm
#import peakutils
#from peakutils.plot import plot as pplot

#matplotlib.rcParams.update({'font.size': 12})

from core.util.units import compute_ft


class FitLogic():
        """
        This file contains a test bed for implementation of new fit
        functions and estimators. Here one can also do stability checks
        with dummy data.

        All methods in the folder logic/fitmethods/ are imported here.

        This is a playground so no conventions have to be
        taken into account. This is completely standalone and does not interact
        with qudi. It only will import the fitting methods from qudi.

        """
        def __init__(self,path_of_qudi=None):

            self.log = logger
            filenames=[]

            if path_of_qudi is None:
                # get from this script the absolte filepath:
                file_path = os.path.realpath(__file__)

                # retrieve the path to the directory of the file:
                script_dir_path = os.path.dirname(file_path)

                # retrieve the path to the directory of the qudi module:
                mod_path = os.path.dirname(script_dir_path)

            else:
                mod_path = path_of_qudi

            fitmodules_path = join(mod_path,'logic','fitmethods')

            if fitmodules_path not in sys.path:
                sys.path.append(fitmodules_path)

            for f in listdir(fitmodules_path):
                if isfile(join(fitmodules_path, f)) and f.endswith(".py"):
                    filenames.append(f[:-3])

            oneD_fit_methods = dict()
            twoD_fit_methods = dict()

            for files in filenames:
                mod = importlib.import_module('{0}'.format(files))
                for method in dir(mod):
                    try:
                        if callable(getattr(mod, method)):
                            #import methods in Fitlogic
                            setattr(FitLogic, method, getattr(mod, method))
                            #add method to dictionary and define what
                            #estimators they have

                            # check if it is a make_<own fuction>_fit method
                            if (str(method).startswith('make_')
                                and str(method).endswith('_fit')):
                                # only add to dictionary if it is not already there
                                if 'twoD' in str(method) and str(method).split('_')[1] not in twoD_fit_methods:
                                    twoD_fit_methods[str(method).split('_')[1]]=[]
                                elif str(method).split('_')[1] not in oneD_fit_methods:
                                    oneD_fit_methods[str(method)[5:-4]]=[]
                            # if there is an estimator add it to the dictionary
                            if 'estimate' in str(method):
                                if 'twoD' in str(method):
                                    try: # if there is a given estimator it will be set or added
                                        if str(method).split('_')[1] in twoD_fit_methods:
                                            twoD_fit_methods[str(method).split('_')[1]]=twoD_fit_methods[str(method).split('_')[1]].append(str(method).split('_')[2])
                                        else:
                                            twoD_fit_methods[str(method).split('_')[1]]=[str(method).split('_')[2]]
                                    except:  # if there is no estimator but only a standard one the estimator is empty
                                        if not str(method).split('_')[1] in twoD_fit_methods:
                                            twoD_fit_methods[str(method).split('_')[1]]=[]
                                else: # this is oneD case
                                    try: # if there is a given estimator it will be set or added
                                        if (str(method).split('_')[1] in oneD_fit_methods and str(method).split('_')[2] is not None):
                                            oneD_fit_methods[str(method).split('_')[1]].append(str(method).split('_')[2])
                                        elif str(method).split('_')[2] is not None:
                                            oneD_fit_methods[str(method).split('_')[1]]=[str(method).split('_')[2]]
                                    except: # if there is no estimator but only a standard one the estimator is empty
                                        if not str(method).split('_')[1] in oneD_fit_methods:
                                            oneD_fit_methods[str(method).split('_')[1]]=[]
                    except:
                        self.log.error('It was not possible to import element {} into FitLogic.'
                                       ''.format(method))
            self.log.info('Methods were included to FitLogic, but only if naming is right: '
                          'make_<own method>_fit. If estimator should be added, the name has')

qudi_fitting = FitLogic()


##############################################################################
##############################################################################

                        #Testing routines

##############################################################################
##############################################################################



def N15_testing():
    """ Test function to implement the estimator for the N15 fit with offset. """
    x_axis = np.linspace(2850, 2860, 101)*1e6

    mod,params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)
#            print('Parameters of the model',mod.param_names)

    p=Parameters()

    p.add('l0_amplitude',value=-1e4)
    p.add('l0_center',value=2850*1e6+abs(np.random.random(1)*8)*1e6)
#            p.add('lorentz0_sigma',value=abs(np.random.random(1)*1)*1e6+0.5*1e6)
    p.add('l0_sigma',value=0.5*1e6)
    p.add('l1_amplitude',value=p['l0_amplitude'].value)
    p.add('l1_center',value=p['l0_center'].value+3.03*1e6)
    p.add('l1_sigma',value=p['l0_sigma'].value)
    p.add('offset',value=100000.)

    data_nice = mod.eval(x=x_axis, params=p)

    data_noisy= data_nice + 6000*np.random.normal(size=x_axis.shape)

    data_smooth_lorentz, offset = qudi_fitting.find_offset_parameter(x_axis,
                                                                     data_noisy)

    print('offset:', offset)

    x_offset = np.array([offset]*len(x_axis))

    plt.figure()
    plt.plot(x_axis, data_noisy, label='noisy data')
    plt.plot(x_axis, data_smooth_lorentz, label='smoothed data')
    plt.plot(x_axis, x_offset, label='offset estimation')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    hf_splitting = 3.03 * 1e6 # Hz

    # filter should always have a length of approx linewidth 1MHz
    points_within_1MHz = len(x_axis)/(x_axis.max()-x_axis.min()) * 1e6

    # filter should have a width of 4 MHz
    x_filter = np.linspace(0,4*points_within_1MHz,4*points_within_1MHz)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0)*(x_filter < len(x_filter)/4),
                                      (x_filter >= len(x_filter)/4)*(x_filter < len(x_filter)*3/4),
                                      (x_filter >= len(x_filter)*3/4)],
                           [1, 0, 1])

    # if the filter is smaller than 3 points a convolution does not make sense
    if len(lorentz) >= 3:
        data_convolved = filters.convolve1d(data_smooth_lorentz,
                                            lorentz/lorentz.sum(),
                                            mode='constant',
                                            cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()]-hf_splitting/2.
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]

    # data_level = data_smooth_lorentz - data_smooth_lorentz.max()
    data_level = data_smooth_lorentz - offset

    # multiply
    minimum_level = data_level.min()

    x_min_level = np.array([minimum_level]*len(x_axis))

    plt.figure()
    plt.plot(x_axis, data_noisy-offset, label='leveled noisy data')
    plt.plot(x_axis, data_level, label='leveled smoothed data')
    plt.plot(x_axis, x_min_level, label='minimum level estimation')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # integral of data:
    function = InterpolatedUnivariateSpline(x_axis, data_level, k=1)
    Integral = function.integral(x_axis[0], x_axis[-1])

    # assume both peaks contribute to the linewidth, so devive by 2:
    sigma = abs(Integral /(np.pi * minimum_level) )/2

    # amplitude = -1*abs(minimum_level*np.pi*sigma)
    amplitude = -abs(minimum_level)

    minimal_sigma = x_axis[1]-x_axis[0]
    maximal_sigma = x_axis[-1]-x_axis[0]

    mod, params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)

    params['l0_amplitude'].set(value=amplitude, max=-1e-6)
    params['l0_center'].set(value=x_axis_min)
    params['l0_sigma'].set(value=sigma, min=minimal_sigma,
                                 max=maximal_sigma)
    params['l1_amplitude'].set(value=params['l0_amplitude'].value,
                               max=-1e-6)
    params['l1_center'].set(value=params['l0_center'].value+hf_splitting,
                            expr='l0_center+3.03*1e6')
    params['l1_sigma'].set(value=params['l0_sigma'].value,
                           min=minimal_sigma, max=maximal_sigma,
                           expr='l0_sigma')
    params['offset'].set(value=offset)

    result = mod.fit(data_noisy, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, data_noisy, label='original data')
    plt.plot(x_axis, result.init_fit,'-y', label='initial values')
    plt.plot(x_axis, result.best_fit,'-r', label='actual fit')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


def N15_testing2():
    """ Test direkt the implemented fit method with simulated data."""

    x_axis = np.linspace(2850, 2860, 101)*1e6

    mod,params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)
#            print('Parameters of the model',mod.param_names)

    p=Parameters()

    p.add('l0_amplitude',value=-3e4)
    p.add('l0_center',value=2850*1e6+abs(np.random.random(1)*8)*1e6)
#            p.add('lorentz0_sigma',value=abs(np.random.random(1)*1)*1e6+0.5*1e6)
    p.add('l0_sigma',value=0.5*1e6)
    p.add('l1_amplitude',value=p['l0_amplitude'].value)
    p.add('l1_center',value=p['l0_center'].value+3.03*1e6)
    p.add('l1_sigma',value=p['l0_sigma'].value)
    p.add('offset',value=100.)

    data_nice = mod.eval(x=x_axis, params=p)

    data_noisy=(data_nice + 14000*np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_lorentziandouble_fit(x_axis, data_noisy,
                                                       estimator=qudi_fitting.estimate_lorentziandouble_N15)

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
    plt.plot(x_axis, result.init_fit,'-y', label='initial values')
    plt.plot(x_axis, result.best_fit,'-r', label='actual fit')
    plt.plot(x_axis, data_nice,'-g', label='actual fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


def N14_testing():
    """ Test function to implement the estimator for the N14 fit with offset. """

    # get the model of the three lorentzian peak, this gives you the
    # ability to get the used parameter container for the fit.
    mod, params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=3)

#    x_axis = np.linspace(2850, 2860, 101)*1e6
    x_axis = np.linspace(2720, 2890, 301)*1e6


    sigma = 1e6  # linewidth
#   sigma = abs(np.random.random(1)*1)+0.5

    amplitude = -1e4

    minimal_linewidth = (x_axis[1]-x_axis[0])/4
    maximal_linewidth = x_axis[-1]-x_axis[0]
    peak_pos1 = 2852*1e6
    offset = 150000
#                x_axis_min = 2850+abs(np.random.random(1)*8)

    params['l0_amplitude'].set(value=amplitude)
    params['l0_center'].set(value=peak_pos1)
    params['l0_sigma'].set(value=sigma)
    params['l1_amplitude'].set(value=amplitude)
    params['l1_center'].set(value=params['l0_center'].value+2.15*1e6)
    params['l1_sigma'].set(value=sigma)
    params['l2_amplitude'].set(value=amplitude)
    params['l2_center'].set(value=params['l1_center'].value+2.15*1e6)
    params['l2_sigma'].set(value=sigma)
    params['offset'].set(value=offset)

    data_noisy=(mod.eval(x=x_axis, params=params) + \
                7000*np.random.normal(size=x_axis.shape))

    data_smooth_lorentz, offset = qudi_fitting.find_offset_parameter(x_axis, data_noisy)

    print('offset', offset)

    # level of the data, that means the offset is subtracted and the real data
    # are present
    data_level = data_smooth_lorentz - offset
    minimum_level = data_level.min()*1.5


    print('minimum level = amplitude:', minimum_level)

    offset_data = np.array([offset]*len(x_axis))

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
    plt.plot(x_axis, data_smooth_lorentz,'-g',linewidth=2.0, label='smoothed data')
    plt.plot(x_axis, offset_data,linewidth=2.0, label='estimated offset')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    plt.figure()
    plt.plot(x_axis, data_level,'-b', label='leveled data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # Create now a filter of length 5MHz, then create a step-wise function with
    # three dips. This step-wise function will be convolved with the smoothed
    # data, where the maximal contribution will be if the peaks are within the
    # filter. Take that to obtain from that the accurate peak position:

    # filter of one dip should always have a length of approx linewidth 1MHz
    points_within_1MHz = len(x_axis)/(x_axis.max()-x_axis.min()) * 1e6

    # filter should have a width of 5MHz
    x_filter = np.linspace(0, 5*points_within_1MHz, 5*points_within_1MHz)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0)                   * (x_filter < len(x_filter)*1/5),
                                      (x_filter >= len(x_filter)*1/5)   * (x_filter < len(x_filter)*2/5),
                                      (x_filter >= len(x_filter)*2/5)   * (x_filter < len(x_filter)*3/5),
                                      (x_filter >= len(x_filter)*3/5)   * (x_filter < len(x_filter)*4/5),
                                      (x_filter >= len(x_filter)*4/5)],
                           [1, 0, 1, 0, 1])

    # if the filter is smaller than 5 points a convolution does not make sense
    if len(lorentz) >= 5:
        data_convolved = filters.convolve1d(data_smooth_lorentz,
                                            lorentz/lorentz.sum(),
                                            mode='constant',
                                            cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()]-2.15*1e6
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]-2.15*1e6

    plt.figure()
    plt.plot(x_axis, data_convolved,'-b', label='Convoluted result')
#    plt.plot(x_axis, data_smooth_lorentz,'-g',linewidth=2.0, label='smoothed data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # In order to perform a smooth integral to obtain the area under the curve
    # make an interpolation of the passed data, in case they are very sparse.
    # That increases the accuracy of the calculated Integral.
    # integral of data corresponds to sqrt(2) * Amplitude * Sigma

    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    function = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
    integrated_area = function.integral(x_axis[0], x_axis[-1])

    # sigma = abs(integrated_area / (minimum_level/np.pi))
    # That is wrong, so commenting out:
    sigma = abs(integrated_area /(np.pi * minimum_level))/1.5

    amplitude = -1*abs(minimum_level)

    # Since the total amplitude of the lorentzian is depending on sigma it makes
    # sense to vary sigma within an interval, which is smaller than the minimal
    # distance between two points. Then the fit algorithm will have a larger
    # range to determine the amplitude properly. That is the main issue with the
    # fit!
    minimal_linewidth = (x_axis[1]-x_axis[0])/4
    maximal_linewidth = x_axis[-1]-x_axis[0]

    # The linewidth of all the lorentzians are set to be the same! that is a
    # physical constraint for the N14 fitting.

    # Fill the parameter container, with the estimated values, which should be
    # passed to the fit algorithm:
    params['l0_amplitude'].set(value=amplitude, max=-1e-6)
    params['l0_center'].set(value=x_axis_min)
    params['l0_sigma'].set(value=sigma, min=minimal_linewidth,
                                 max=maximal_linewidth)
    params['l1_amplitude'].set(value=amplitude, max=-1e-6)
    params['l1_center'].set(value=x_axis_min+2.15*1e6,
                                  expr='l0_center+2.15*1e6')
    params['l1_sigma'].set(value=sigma, min=minimal_linewidth,
                                 max=maximal_linewidth, expr='l0_sigma')
    params['l2_amplitude'].set(value=amplitude, max=-1e-6)
    params['l2_center'].set(value=x_axis_min+2.15*1e6,
                                  expr='l0_center+4.3*1e6')
    params['l2_sigma'].set(value=sigma, min=minimal_linewidth,
                                 max=maximal_linewidth, expr='l0_sigma')
    params['offset'].set(value=offset)


    result = mod.fit(data_noisy, x=x_axis, params=params)

    result.params['offset'].unit = 'Hz'

#    print('result:',dir(result))

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
#            plt.plot(x_axis, data_smooth_lorentz,'-g',linewidth=2.0, label='smoothed data')
#            plt.plot(x_axis, data_convolved,'-y',linewidth=2.0, label='convolved data')
#            plt.plot(x_axis, result.init_fit,'-y', label='initial fit')
#            plt.plot(x, result2.best_fit,'-r', label='fit')
    plt.plot(x_axis, result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis, result.init_fit,'-g',label='initial fit')
#            plt.plot(x_axis, data_test,'-k', label='test data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    return result

def N14_testing2():
    """ Test direkt the implemented fit method with simulated data."""

    # get the model of the three lorentzian peak, this gives you the
    # ability to get the used parameter container for the fit.
    mod, params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=3)

    x_axis = np.linspace(2845, 2860, 101)*1e6

    sigma = 1e6  # linewidth
#   sigma = abs(np.random.random(1)*1)+0.5

    amplitude = -3e4

    minimal_linewidth = (x_axis[1]-x_axis[0])/4
    maximal_linewidth = x_axis[-1]-x_axis[0]
    peak_pos1 = 2852*1e6
    offset = 150000
#                x_axis_min = 2850+abs(np.random.random(1)*8)

    params['l0_amplitude'].set(value=amplitude)
    params['l0_center'].set(value=peak_pos1)
    params['l0_sigma'].set(value=sigma)
    params['l1_amplitude'].set(value=amplitude)
    params['l1_center'].set(value=params['l0_center'].value+2.15*1e6)
    params['l1_sigma'].set(value=sigma)
    params['l2_amplitude'].set(value=amplitude)
    params['l2_center'].set(value=params['l1_center'].value+2.15*1e6)
    params['l2_sigma'].set(value=sigma)
    params['offset'].set(value=offset)

    data_noisy=(mod.eval(x=x_axis, params=params) + \
                5000*np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_lorentziantriple_fit(x_axis, data_noisy,
                                                       estimator=qudi_fitting.estimate_lorentziantriple_N14)

    print(result.fit_report())

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
#            plt.plot(x_axis, data_smooth_lorentz,'-g',linewidth=2.0, label='smoothed data')
#            plt.plot(x_axis, data_convolved,'-y',linewidth=2.0, label='convolved data')
#            plt.plot(x_axis, result.init_fit,'-y', label='initial fit')
#            plt.plot(x, result2.best_fit,'-r', label='fit')
    plt.plot(x_axis, result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis, result.init_fit,'-g',label='initial fit')
#            plt.plot(x_axis, data_test,'-k', label='test data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


def N14_testing_data():
    """ Test the N14 fit with data from file. """

    # get the model of the three lorentzian peak, this gives you the
    # ability to get the used parameter container for the fit.
    mod, params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=3)

    # you can insert the whole path with the windows separator
    # symbol \ just use the r in front of the string to indicated
    # that this is a raw input. The os package will do the rest.
    path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\2016\2016-07\2016-07-05 N14 fit fails\20160705-1147-41_n14_fit_fails_60MHz_span_ODMR_data.dat')
    data = np.loadtxt(path)

    # The data for the fit:
    x_axis = data[:,0]
    data_noisy = data[:,1]

    # Estimate the initial parameters
    # ===============================


    # find the offset parameter, which should be in the fit the zero
    # level.
    data_smooth_lorentz, offset = qudi_fitting.find_offset_parameter(x_axis, data_noisy)

    offset_array = np.zeros(len(x_axis))+offset

    # plot all the current results:
    plt.plot(x_axis, data_smooth_lorentz, label='smoothed data')
    plt.plot(x_axis, data_noisy, label='noisy data')
    plt.plot(x_axis, offset_array, label='calculated offset')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # filter of one dip should always have a length of approx linewidth 1MHz
    points_within_1MHz = len(x_axis)/(x_axis.max()-x_axis.min()) * 1e6
#                print(points_within_1MHz)

    # filter should have a width of 5MHz
    x_filter = np.linspace(0, 5*points_within_1MHz, 5*points_within_1MHz)
    lorentz = np.piecewise(x_filter, [(x_filter >= 0)                   * (x_filter < len(x_filter)*1/5),
                                      (x_filter >= len(x_filter)*1/5)   * (x_filter < len(x_filter)*2/5),
                                      (x_filter >= len(x_filter)*2/5)   * (x_filter < len(x_filter)*3/5),
                                      (x_filter >= len(x_filter)*3/5)   * (x_filter < len(x_filter)*4/5),
                                      (x_filter >= len(x_filter)*4/5)],
                           [1, 0, 1, 0, 1])

    plt.plot(x_filter/5, lorentz, label='convolution pattern')
    plt.axis([-0.5, 5.5, -0.05, 1.05])
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('relative intensity')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
#                print('offset', offset)


    # if the filter is smaller than 5 points a convolution does not
    # make sense
    if len(lorentz) >= 5:

        # perform a convolution of the data
        data_convolved = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(), mode='constant', cval=data_smooth_lorentz.max())
        x_axis_min = x_axis[data_convolved.argmin()]-2.15*1e6
    else:
        x_axis_min = x_axis[data_smooth_lorentz.argmin()]-2.15*1e6


    plt.plot(x_axis, data_smooth_lorentz, label='smoothed data')
#                plt.plot(x_axis, data_noisy)
#                plt.plot(x_axis, offset_array)
    plt.plot(x_axis, data_convolved, label='Result after convolution with pattern')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
#                print('x_axis_min', x_axis_min)

    # level of the data, that means the offset is subtracted and
    # the real data are present
    data_level = data_smooth_lorentz - data_smooth_lorentz.mean()
#                data_level = data_smooth_lorentz - data_smooth_lorentz.max() # !!! previous version !!!
    minimum_level = data_level.min()

    # In order to perform a smooth integral to obtain the area
    # under the curve make an interpolation of the passed data, in
    # case they are very sparse. That increases the accuracy of the
    # calculated Integral.
    # integral of data corresponds to sqrt(2) * Amplitude * Sigma

    smoothing_spline = 1 # must be 1<= smoothing_spline <= 5
    interpol_func = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
    integrated_area = interpol_func.integral(x_axis[0], x_axis[-1])

    # set the number of interpolated points
    num_int_points = 1000
    x_interpolated_values = np.linspace(x_axis.min(), x_axis.max(), num_int_points)

    # and use now the interpolate function to generate the data.
#                plt.plot(x_interpolated_values, interpol_func(x_interpolated_values))
#                plt.plot(x_axis, data_level)
#                plt.show()


    sigma = abs(integrated_area /(np.pi * minimum_level) )
#                sigma = abs(integrated_area /(minimum_level/np.pi ) ) # !!! previous version !!!

    amplitude = -1*abs(minimum_level*np.pi*sigma)


    # Since the total amplitude of the lorentzian is depending on
    # sigma it makes sense to vary sigma within an interval, which
    # is smaller than the minimal distance between two points. Then
    # the fit algorithm will have a larger range to determine the
    # amplitude properly. That is the main issue with the fit.
    linewidth = sigma
    minimal_linewidth = x_axis[1]-x_axis[0]
    maximal_linewidth = x_axis[-1]-x_axis[0]
#                print('minimal_linewidth:', minimal_linewidth, 'maximal_linewidth:', maximal_linewidth)

    # Create the parameter container, with the estimated values, which
    # should be passed to the fit algorithm
    parameters = Parameters()

    #            (Name,                  Value,          Vary, Min,             Max,           Expr)
    parameters.add('l0_amplitude', value=amplitude,                                                  max=-1e-6)
    parameters.add('l0_center',    value=x_axis_min)
    parameters.add('l0_sigma',     value=linewidth,                           min=minimal_linewidth, max=maximal_linewidth)
    parameters.add('l1_amplitude', value=parameters['l0_amplitude'].value,                     max=-1e-6)
    parameters.add('l1_center',    value=parameters['l0_center'].value+2.15*1e6,                                      expr='lorentz0_center+2.15*1e6')
    parameters.add('l1_sigma',     value=parameters['l0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
    parameters.add('l2_amplitude', value=parameters['l0_amplitude'].value,                     max=-1e-6)
    parameters.add('l2_center',    value=parameters['l1_center'].value+2.15*1e6,                                      expr='lorentz0_center+4.3*1e6')
    parameters.add('l2_sigma',     value=parameters['l0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
    parameters.add('c',                  value=data_smooth_lorentz.max())


    result = qudi_fitting.make_N14_fit(x_axis, data_noisy)

    print(result.fit_report())

    plt.plot(x_axis, data_noisy,'-b', label='data')
#            plt.plot(x_axis, data_smooth_lorentz,'-g',linewidth=2.0, label='smoothed data')
#            plt.plot(x_axis, data_convolved,'-y',linewidth=2.0, label='convolved data')
#            plt.plot(x_axis, result.init_fit,'-y', label='initial fit')
#            plt.plot(x, result2.best_fit,'-r', label='fit')
    plt.plot(x_axis,result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis,result.init_fit,'-g',label='initial fit')
#            plt.plot(x_axis, data_test,'-k', label='test data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()



def N14_testing_data2():
    """ Test the N14 fit with data from file. """

    # get the model of the three lorentzian peak, this gives you the
    # ability to get the used parameter container for the fit.
    mod, params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=3)

    # you can insert the whole path with the windows separator
    # symbol \ just use the r in front of the string to indicated
    # that this is a raw input. The os package will do the rest.
    path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\Software\QuDi-Git\qudi\pulsedODMRdata.csv')
    data = np.genfromtxt(path,delimiter=',')
#    data = np.loadtxt(path, delimiter=',')
#    print(data)

    # The data for the fit:
    x_axis = data[:,0]*1e8
    data_noisy = data[:,1]


    result = qudi_fitting.make_N14_fit(x_axis, data_noisy)

    print(result.fit_report())

    plt.plot(x_axis, data_noisy,'-b', label='data')
    plt.plot(x_axis,result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis,result.init_fit,'-g',label='initial fit')
#            plt.plot(x_axis, data_test,'-k', label='test data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


def gaussianpeak_testing():
    """ Test the Gaussian peak or dip estimator. """

    x_axis = np.linspace(0, 5, 50)

    ampl = 10000
    center = 3
    sigma = 1
    offset = 10000

    mod_final, params = qudi_fitting.make_gaussoffset_model()
    data_noisy = mod_final.eval(x=x_axis, amplitude=ampl, center=center,
                                sigma=sigma, offset=offset) + \
                                4000*abs(np.random.normal(size=x_axis.shape))

    stepsize = abs(x_axis[1] - x_axis[0])
    n_steps = len(x_axis)


    # Smooth the provided data, so that noise fluctuations will
    # not disturb the parameter estimation.
    std_dev = 2
    data_smoothed = filters.gaussian_filter1d(data_noisy, std_dev)

    plt.figure()
    plt.plot(x_axis, data_noisy, label='data')
    plt.plot(x_axis, data_smoothed, label='smoothed data')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # Define constraints
    # maximal and minimal the length of the given array to the right and to the
    # left:
    center_min = (x_axis[0]) - n_steps * stepsize
    center_max = (x_axis[-1]) + n_steps * stepsize
    ampl_min = 0
    sigma_min = stepsize
    sigma_max = 3 * (x_axis[-1] - x_axis[0])

#    params['amplitude'].min = 100  # that is already noise from APD
#    params['amplitude'].max = data_noisy.max()
#    params['sigma'].min = stepsize
#    params['sigma'].max = 3 * (x_axis[-1] - x_axis[0])

    # not very general to set a such a constaint on offset:
#    params['offset'].min = 0.  # that is already noise from APD
#    params['offset'].max = data_noisy.max() #* params['sigma'].value * np.sqrt(2 * np.pi)*2.


    # set parameters
    offset = data_smoothed.min()
    params['offset'].set(value=offset)

    # it is more reliable to obtain select the maximal value rather then
    # calculating the first moment of the gaussian distribution (which is the
    # mean value), since it is unreliable if the distribution begins or ends at
    # the edges of the data:
    mean_val_calc =  np.sum(x_axis*(data_smoothed)) / np.sum(data_smoothed)
    center_val = x_axis[np.argmax(data_smoothed)]
    params['center'].set(value=center_val,
                         min=center_min, max=center_max)

    # params['sigma'].value = (x_axis.max() - x_axis.min()) / 3.

    # calculate the second moment of the gaussian distribution: int (x^2 * f(x) dx)
    mom2 = np.sum((x_axis)**2 * (data_smoothed)) / np.sum(data_smoothed)

    # and use the standard formula to obtain the standard deviation:
    #   sigma^2 = int( (x-mean)^2 f(x) dx ) = int (x^2 * f(x) dx) - mean^2

    print("mom2", mom2)
    print("std: ", np.sqrt(abs(mom2 - mean_val_calc**2)))

    # if the mean is situated at the edges of the distribution then this
    # procedure performs better then setting the initial value for sigma to
    # 1/3 of the length of the distibution since the calculated value for the
    # mean is then higher, which will decrease eventually the initial value for
    # sigma. But if the peak values is within the distribution the standard
    # deviation formula performs even better:
    params['sigma'].set(value=np.sqrt(abs(mom2 - mean_val_calc**2)),
                        min=sigma_min, max=sigma_max)

    # do not set the maximal amplitude value based on the distribution, since
    # the fit will fail if the peak is at the edges or beyond the range of the
    # x values.
    params['amplitude'].set(value=data_smoothed.max()-data_smoothed.min(),
                            min=ampl_min)



    result = mod_final.fit(data_noisy, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
    plt.plot(x_axis,result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis,result.init_fit,'-g',label='initial fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(result.fit_report())

def gaussianpeak_testing2():
    """ Test the implemented Gaussian peak fit. """

    x_axis = np.linspace(0, 5, 11)

    ampl = 10000
    center = 3
    sigma = 1
    offset = 10000

    mod_final, params = qudi_fitting.make_gaussoffset_model()
    data_noisy = mod_final.eval(x=x_axis, amplitude=ampl, center=center,
                                sigma=sigma, offset=offset) + \
                                2000*abs(np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_gaussoffsetpeak_fit(x_axis=x_axis, data=data_noisy)

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
    plt.plot(x_axis, result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis, result.init_fit,'-g',label='initial fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(result.fit_report())

def gaussiandip_testing2():
    """ Test the implemented Gaussian dip fit. """

    x_axis = np.linspace(0, 5, 11)

    ampl = -10000
    center = 3
    sigma = 1
    offset = 10000

    mod_final, params = qudi_fitting.make_gaussoffset_model()
    data_noisy = mod_final.eval(x=x_axis, amplitude=ampl, center=center,
                                sigma=sigma, offset=offset) + \
                                5000*abs(np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_gaussoffsetdip_fit(x_axis=x_axis, data=data_noisy)

    plt.figure()
    plt.plot(x_axis, data_noisy,'-b', label='data')
    plt.plot(x_axis, result.best_fit,'-r', label='best fit result')
    plt.plot(x_axis, result.init_fit,'-g',label='initial fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(result.fit_report())


def gaussianlinearoffset_testing():
    """ Test the implemented Estimator for Gaussian peak with linear offset """

    x_axis = np.linspace(0, 5, 30)

    mod_final, params = qudi_fitting.make_gausslinearoffset_model()

    slope = -10000
    amplitude = 100000
    center = 3
    sigma = 0.62863
    offset = 100

    data_noisy = mod_final.eval(x=x_axis, slope=slope, amplitude=amplitude,
                               center=center, sigma=sigma, offset=offset) + \
                               12000 * abs(np.random.normal(size=x_axis.shape))

    # try at first a fit with the ordinary gauss function
    res_ordinary_gauss = qudi_fitting.make_gaussoffsetpeak_fit(x_axis=x_axis,
                                                               data=data_noisy)

    # subtract the result and perform again a linear fit:
    data_subtracted = data_noisy - res_ordinary_gauss.best_fit

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, res_ordinary_gauss.best_fit, label="initial gauss fit")
    plt.plot(x_axis, data_subtracted, label="data subtacted")
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    res_linear = qudi_fitting.make_linear_fit(x_axis=x_axis,
                                              data=data_subtracted)

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, res_linear.best_fit, label="linear fit on data")
    plt.plot(x_axis, data_subtracted, label="data subtacted")
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # this way works much better than performing at first a linear fit,
    # subtracting the fit and make an ordinary gaussian fit. Especially for a
    # peak at the borders, this method is much more beneficial.

    # assign the obtained values for the initial fit:
    params['offset'] = res_ordinary_gauss.params['offset']
    params['center'] = res_ordinary_gauss.params['center']
    params['amplitude'] = res_ordinary_gauss.params['amplitude']
    params['sigma'] = res_ordinary_gauss.params['sigma']
    params['slope'] = res_linear.params['slope']


    result = mod_final.fit(data_noisy, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, result.init_fit, label='init fit')
    plt.plot(x_axis, result.best_fit, label='best fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
#    print(result.fit_report())

def gaussianlinearoffset_testing2():
    """ Test the implemented Gaussian peak with linear offset fit. """

    x_axis = np.linspace(0, 5, 30)

    mod_final,params = qudi_fitting.make_gaussianwithslope_model()

    slope = -10000
    amplitude = 100000
    center = 6
    sigma = 0.62863
    offset = 100

    data_noisy=mod_final.eval(x=x_axis, slope=slope, amplitude=amplitude,
                              center=center, sigma=sigma, offset=offset) + \
                              10000 * abs(np.random.normal(size=x_axis.shape))

    result=qudi_fitting.make_gausspeaklinearoffset_fit(x_axis=x_axis, data=data_noisy)

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, result.init_fit,'-g', label='init')
    plt.plot(x_axis, result.best_fit,'-r', label='fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(result.fit_report())

def gaussianlinearoffset_testing_data():

    x = np.linspace(0, 5, 30)
    x_nice=np.linspace(0, 5, 101)

    mod_final,params = qudi_fitting.make_gaussianwithslope_model()

    data=np.loadtxt("./../1D_shllow.csv")
    data_noisy=data[:,1]
    data_fit=data[:,3]
    x=data[:,2]


    update=dict()
    update["slope"]={"min":-np.inf,"max":np.inf}
    update["offset"]={"min":-np.inf,"max":np.inf}
    update["sigma"]={"min":-np.inf,"max":np.inf}
    update["center"]={"min":-np.inf,"max":np.inf}
    update["amplitude"]={"min":-np.inf,"max":np.inf}
    result=qudi_fitting.make_gaussianwithslope_fit(x_axis=x, data=data_noisy, add_params=update)
#
##
#    gaus=gaussian(3,5)
#    qudi_fitting.data_smooth = filters.convolve1d(qudi_fitting.data_noisy, gaus/gaus.sum(),mode='mirror')

    plt.plot(x,data_noisy,label="data")
    plt.plot(x,data_fit,"k",label="old fit")
    plt.plot(x,result.init_fit,'-g',label='init')
    plt.plot(x,result.best_fit,'-r',label='fit')
    plt.legend()
    plt.show()
    print(result.fit_report())



def two_gaussian_peak_testing():
    """ Test the implemented estimator for two gaussian peaks with offset """

    start=100000
    stop= 500000
    num_points=int((stop-start)/2000)
    x_axis = np.linspace(start, stop, num_points)

    mod, params = qudi_fitting.make_multiplegaussianoffset_model(no_of_functions=2)


    amplitude0 = 75000+np.random.random(1)*50000
    amplitude1 = amplitude0*1.5
#    splitting = 100000  # abs(np.random.random(1)*100000)
    splitting = abs(np.random.random(1)*200000)
    center0 = 160000
#    center1 = 300000
    center1 = center0 + splitting
    sigma0 = 25000+np.random.random(1)*20000
    sigma1 = 25000+np.random.random(1)*20000
    splitting = 100000  # abs(np.random.random(1)*300000)

    params['g0_amplitude'].value = amplitude0
    params['g0_center'].value = center0
    params['g0_sigma'].value = sigma0
    params['g1_amplitude'].value = amplitude1
    params['g1_center'].value = center1
    params['g1_sigma'].value = sigma1
    params['offset'].value = 0


    data_noisy=(mod.eval(x=x_axis,params=params)
                            + 20000*np.random.normal(size=x_axis.shape))

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
#    plt.plot(x_axis, result.init_fit,'-g', label='init')
#    plt.plot(x_axis, result.best_fit,'-r', label='fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    threshold_fraction=0.4
    minimal_threshold=0.2
    sigma_threshold_fraction=0.3


    mod_lor, params_lor = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)

    error, params_lor = qudi_fitting.estimate_lorentziandouble_dip(x_axis=x_axis,
                                                     data=-data_noisy,
                                                     params=params_lor,
                                                     threshold_fraction=threshold_fraction,
                                                     minimal_threshold=minimal_threshold,
                                                     sigma_threshold_fraction=sigma_threshold_fraction)

    result_lor = mod_lor.fit(-data_noisy, x=x_axis, params=params_lor)

    plt.figure()
    plt.plot(x_axis, -data_noisy, label="data")
    plt.plot(x_axis, result_lor.init_fit, label='init lorentz fit')
    plt.plot(x_axis, result_lor.best_fit, label='actual lorentz fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    mod, params = qudi_fitting.make_multiplegaussianoffset_model(no_of_functions=2)



    params['g0_amplitude'].value = -params_lor['l0_amplitude'].value
    params['g0_center'].value = params_lor['l0_center'].value
    params['g0_sigma'].value = params_lor['l0_sigma'].value/(np.sqrt(2*np.log(2)))
    params['g1_amplitude'].value = -params_lor['l1_amplitude'].value
    params['g1_center'].value = params_lor['l1_center'].value
    params['g1_sigma'].value = params_lor['l1_sigma'].value/(np.sqrt(2*np.log(2)))
    params['offset'].value = -params_lor['offset'].value


    result = mod.fit(data_noisy, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, result.init_fit, label='initial value double gauss')
    plt.plot(x_axis, result.best_fit, label='fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

#
#    return


#                np.savetxt('data',data_noisy)

#                data_noisy=np.loadtxt('data')
#                para=Parameters()
#                result=qudi_fitting.make_doublegaussian_fit(axis=x,data=data_noisy,add_parameters=para)
#
    #make the filter an extra function shared and usable for other functions
#    gaus=gaussian(10,10)
#    data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')
#
##                set optimal thresholds
#    threshold_fraction=0.4
#    minimal_threshold=0.2
#    sigma_threshold_fraction=0.3
#
#
#    qudi_fitting.estimate_lorentziandouble_dip()
#
#    error, \
#    sigma0_argleft, dip0_arg, sigma0_argright, \
#    sigma1_argleft, dip1_arg , sigma1_argright = \
#    qudi_fitting._search_double_dip(x, data_smooth*-1,
#                            threshold_fraction=threshold_fraction,
#                            minimal_threshold=minimal_threshold,
#                            sigma_threshold_fraction=sigma_threshold_fraction,
#                            make_prints=False)
#
#    print(x[sigma0_argleft], x[dip0_arg], x[sigma0_argright], x[sigma1_argleft], x[dip1_arg], x[sigma1_argright])
#    print(x[dip0_arg], x[dip1_arg])
#
#    plt.plot((x[sigma0_argleft], x[sigma0_argleft]), ( data_noisy.min() ,data_noisy.max()), 'b-')
#    plt.plot((x[sigma0_argright], x[sigma0_argright]), (data_noisy.min() ,data_noisy.max()), 'b-')
#
#    plt.plot((x[sigma1_argleft], x[sigma1_argleft]), ( data_noisy.min() ,data_noisy.max()), 'k-')
#    plt.plot((x[sigma1_argright], x[sigma1_argright]), ( data_noisy.min() ,data_noisy.max()), 'k-')
#
#    paramdict = dict()
#    paramdict['gaussian0_amplitude'] = {'gaussian0_amplitude':amplitude}
#    paramdict['gaussian0_center'] = {'gaussian0_center':160000}
#    paramdict['gaussian0_sigma'] = {'gaussian0_sigma':sigma0}
#    paramdict['gaussian1_amplitude'] = {'gaussian1_amplitude':amplitude*1.5}
#    paramdict['gaussian1_center'] = {'gaussian1_center':300000}
#    paramdict['gaussian1_sigma'] = {'gaussian1_sigma':sigma1}
#    paramdict['c'] = {'c':0}
#
#    result=qudi_fitting.make_doublegaussian_fit(x,data_noisy,add_parameters = paramdict,estimator='gated_counter',
#                            threshold_fraction=threshold_fraction,
#                            minimal_threshold=minimal_threshold,
#                            sigma_threshold_fraction=sigma_threshold_fraction)
#
#    plt.plot((result.init_values['gaussian0_center'], result.init_values['gaussian0_center']), ( data_noisy.min() ,data_noisy.max()), 'r-')
#    plt.plot((result.init_values['gaussian1_center'], result.init_values['gaussian1_center']), ( data_noisy.min() ,data_noisy.max()), 'r-')
#    print(result.init_values['gaussian0_center'],result.init_values['gaussian1_center'])
##                gaus=gaussian(20,10)
##                data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')
##                data_der=np.gradient(data_smooth)
#    print(result.fit_report())
#    print(result.message)
#    print(result.success)
##                print(result.params)
#    print(result.errorbars)
#
#######################################################

    #TODO: check if adding  #,fit_kws={"ftol": 1e-4, "xtol": 1e-4, "gtol": 1e-4} to model.fit can help to get errorbars

#####################################################
    try:
        plt.plot(x, data_noisy, '-b')
        plt.plot(x, data_smooth, '-g')
#                    plt.plot(x, data_der*10, '-r')
#                    print(result.best_values['gaussian0_center']/1000,result.best_values['gaussian1_center']/1000)
        plt.plot(x,result.init_fit,'-y')
        plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
        plt.show()


    except:
        print('exception')


#
#                plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'-r')#
#                plt.show()
#
#                print('Peaks:',p['gaussian0_center'].value,p['gaussian1_center'].value)
#                print('Estimator:',result.init_values['gaussian0_center'],result.init_values['gaussian1_center'])
#
#                data=-1*data_smooth+data_smooth.max()
#                 print('peakutils',x[ peakutils.indexes(data, thres=1.1/max(data), min_dist=1)])
#                indices= peakutils.indexes(data, thres=5/max(data), min_dist=2)
#                print('Peakutils',x[indices])
#                pplot(x,data,indices)


def two_gaussian_peak_testing2():
    """ Test the implemented Two Gaussian peak with offset fit. """

    start=100000
    stop= 500000
    num_points=int((stop-start)/2000)
    x_axis = np.linspace(start, stop, num_points)

    mod, params = qudi_fitting.make_multiplegaussianoffset_model(no_of_functions=2)


    amplitude0 = 75000+np.random.random(1)*50000
    amplitude1 = amplitude0*1.5
#    splitting = 100000  # abs(np.random.random(1)*100000)
    splitting = abs(np.random.random(1)*200000)
    center0 = 160000
#    center1 = 300000
    center1 = center0 + splitting
    sigma0 = 25000+np.random.random(1)*20000
    sigma1 = 25000+np.random.random(1)*20000
    splitting = 100000  # abs(np.random.random(1)*300000)

    params['g0_amplitude'].value = amplitude0
    params['g0_center'].value = center0
    params['g0_sigma'].value = sigma0
    params['g1_amplitude'].value = amplitude1
    params['g1_center'].value = center1
    params['g1_sigma'].value = sigma1
    params['offset'].value = 0


    data_noisy=(mod.eval(x=x_axis,params=params)
                            + 20000*np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_twogausspeakoffset_fit(x_axis=x_axis,
                                                      data=data_noisy)

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, result.init_fit, label='initial value double gauss')
    plt.plot(x_axis, result.best_fit, label='fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

def two_gaussian_dip_testing2():
    """ Test the implemented Two Gaussian dip with offset fit. """

    start=100000
    stop= 500000
    num_points=int((stop-start)/2000)
    x_axis = np.linspace(start, stop, num_points)

    mod, params = qudi_fitting.make_multiplegaussoffset_model(no_of_functions=2)


    amplitude0 = -75000+np.random.random(1)*50000
    amplitude1 = amplitude0*1.5
#    splitting = 100000  # abs(np.random.random(1)*100000)
    splitting = abs(np.random.random(1)*200000)
    center0 = 160000
#    center1 = 300000
    center1 = center0 + splitting
    sigma0 = 2500+np.random.random(1)*8000
    sigma1 = 2500+np.random.random(1)*8000
    splitting = 100000  # abs(np.random.random(1)*300000)
    offset = 200000

    params['g0_amplitude'].value = amplitude0
    params['g0_center'].value = center0
    params['g0_sigma'].value = sigma0
    params['g1_amplitude'].value = amplitude1
    params['g1_center'].value = center1
    params['g1_sigma'].value = sigma1
    params['offset'].value = offset


    data_noisy=(mod.eval(x=x_axis,params=params)
                            + 30000*np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_twogaussdipoffset_fit(x_axis=x_axis,
                                                      data=data_noisy)

    plt.figure()
    plt.plot(x_axis, data_noisy, label="data")
    plt.plot(x_axis, result.init_fit, label='initial value double gauss')
    plt.plot(x_axis, result.best_fit, label='fit')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts (#)')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())




def gaussian_twoD_testing():
    """ Implement and check the estimator for a 2D gaussian fit. """

    data = np.empty((121,1))
    amplitude=np.random.normal(3e5,1e5)
    center_x=91+np.random.normal(0,0.8)
    center_y=14+np.random.normal(0,0.8)
    sigma_x=np.random.normal(0.7,0.2)
    sigma_y=np.random.normal(0.7,0.2)
    offset=0
    x = np.linspace(90,92,11)
    y = np.linspace(13,15,12)
    xx, yy = np.meshgrid(x, y)

    axes=(xx.flatten(), yy.flatten())

    theta_here=10./360.*(2*np.pi)

#            data=qudi_fitting.twoD_gaussian_function((xx,yy),*(amplitude,center_x,center_y,sigma_x,sigma_y,theta_here,offset))
    gmod,params = qudi_fitting.make_twoDgaussian_model()

    data = gmod.eval(x=axes, amplitude=amplitude, center_x=center_x,
                     center_y=center_y, sigma_x=sigma_x, sigma_y=sigma_y,
                     theta=theta_here, offset=offset)
    data += 50000*np.random.random_sample(np.shape(data))

    gmod, params = qudi_fitting.make_twoDgaussian_model()

    para=Parameters()
#    para.add('theta',vary=False)
#    para.add('center_x',expr='0.5*center_y')
#    para.add('sigma_x',min=0.2*((92.-90.)/11.), max=   10*(x[-1]-y[0]) )
#    para.add('sigma_y',min=0.2*((15.-13.)/12.), max=   10*(y[-1]-y[0]))
#    para.add('center_x',value=40,min=50,max=100)

    result = qudi_fitting.make_twoDgaussian_fit(xy_axes=axes, data=data)#,add_parameters=para)

#
#            FIXME: What does "Tolerance seems to be too small." mean in message?
#            print(result.message)
    plt.close('all')

    fig, ax = plt.subplots(1, 1)
    ax.hold(True)
    ax.imshow(result.data.reshape(len(y),len(x)),
              cmap=plt.cm.jet, origin='bottom', extent=(x.min(), x.max(),
                                       y.min(), y.max()),interpolation="nearest")
    ax.contour(x, y, result.best_fit.reshape(len(y),len(x)), 8
                , colors='w')
    plt.show()
#    plt.close('all')

    print(result.fit_report())

#            print('Message:',result.message)








def useful_object_variables():
    x = np.linspace(2800, 2900, 101)


    ##there are useful builtin models: Constantmodel(), LinearModel(),GaussianModel()
#                LorentzianModel(),DampedOscillatorModel()

    #but you can also define your own:
    model,params = qudi_fitting.make_lorentzian_model()
#            print('Parameters of the model',model.param_names)

    ##Parameters:
    p=Parameters()

    p.add('amplitude',value=-35)
    p.add('center',value=2845+abs(np.random.random(1)*8))
    p.add('sigma',value=abs(np.random.random(1)*1)+3)
    p.add('c',value=100.)


    data_noisy=(model.eval(x=x,params=p)
                            + 0.5*np.random.normal(size=x.shape))
    para=Parameters()
#            para.add('sigma',vary=False,min=3,max=4)
    #also expression possible

    result=qudi_fitting.make_lorentzian_fit(x, data_noisy, add_params=para)

#            print('success',result.success)
#            print('best value',result.best_values['center'])
##
#            print('Fit report:',result.fit_report())

    plt.plot(x,data_noisy)
#            plt.plot(x,result.init_fit,'-g')
#            plt.plot(x,result.best_fit,'-r')
    plt.show()

#            data_smooth,offset=qudi_fitting.find_offset_parameter(x,data_noisy)
#            plt.plot(data_noisy,'-b')
#            plt.plot(data_smooth,'-r')
#            plt.show()

def double_lorentzdip_testing():
    """ Test function to implement the estimator for the double lorentz dip
        fit with offset. """

    start = 2800
    stop = 2950
    num_points = int((stop-start)/2)*1
    x_axis = np.linspace(start, stop, num_points)

    x_nice = np.linspace(start, stop, num_points*4)

    mod,params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)
#    print('Parameters of the model',mod.param_names)

    p=Parameters()

    #============ Create data ==========

#                center=np.random.random(1)*50+2805
#            p.add('center',max=-1)
    p.add('l0_amplitude',value=-abs(np.random.random(1)*2+20))
    p.add('l0_center',value=np.random.random(1)*150.0+2800)
    p.add('l0_sigma',value=abs(np.random.random(1)*1.+1.))
    p.add('l1_center',value=np.random.random(1)*150.0+2800)
    p.add('l1_sigma',value=abs(np.random.random(1)*4.+1.))
    p.add('l1_amplitude',value=-abs(np.random.random(1)*1+10))

    p.add('offset',value=100.)

    data_noisy=(mod.eval(x=x_axis,params=p)
                + 6*np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_lorentziandouble_fit(x_axis=x_axis, data=data_noisy,
                estimator=qudi_fitting.estimate_lorentziandouble_dip)

    data_smooth, offset = qudi_fitting.find_offset_parameter(x_axis, data_noisy)

#                print('Offset:',offset)
#                print('Success:',result.success)
#                print(result.message)
#                print(result.lmdif_message)
#                print(result.fit_report(show_correl=False))

    data_level = data_smooth - offset

    threshold_fraction = 0.3
    minimal_threshold =  0.01
    sigma_threshold_fraction = 0.3

    ret_val = qudi_fitting._search_double_dip(x_axis, data_level,
                                              threshold_fraction,
                                              minimal_threshold,
                                              sigma_threshold_fraction)

    error = ret_val[0]
    sigma0_argleft, dip0_arg, sigma0_argright = ret_val[1:4]
    sigma1_argleft, dip1_arg , sigma1_argright = ret_val[4:7]

    if dip0_arg == dip1_arg:
        lorentz0_amplitude = data_level[dip0_arg]/2.
        lorentz1_amplitude = lorentz0_amplitude
    else:
        lorentz0_amplitude = data_level[dip0_arg]
        lorentz1_amplitude = data_level[dip1_arg]

    lorentz0_center = x_axis[dip0_arg]
    lorentz1_center = x_axis[dip1_arg]


    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    function = InterpolatedUnivariateSpline(x_axis, data_level,
                                            k=smoothing_spline)
    numerical_integral_0 = function.integral(x_axis[sigma0_argleft],
                                             x_axis[sigma0_argright])

    lorentz0_sigma = abs(numerical_integral_0 / (np.pi * lorentz0_amplitude))

    numerical_integral_1 = numerical_integral_0

    lorentz1_sigma = abs(numerical_integral_1 / (np.pi * lorentz1_amplitude))

    stepsize = x_axis[1]-x_axis[0]
    full_width = x_axis[-1]-x_axis[0]
    n_steps = len(x_axis)

    mod, params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)

    if lorentz0_center < lorentz1_center:
        params['l0_amplitude'].set(value=lorentz0_amplitude, max=-0.01)
        params['l0_sigma'].set(value=lorentz0_sigma, min=stepsize/2,
                               max=full_width*4)
        params['l0_center'].set(value=lorentz0_center,
                                min=(x_axis[0])-n_steps*stepsize,
                                max=(x_axis[-1])+n_steps*stepsize)
        params['l1_amplitude'].set(value=lorentz1_amplitude, max=-0.01)
        params['l1_sigma'].set(value=lorentz1_sigma, min=stepsize/2,
                               max=full_width*4)
        params['l1_center'].set(value=lorentz1_center,
                                min=(x_axis[0])-n_steps*stepsize,
                                max=(x_axis[-1])+n_steps*stepsize)
    else:
        params['l0_amplitude'].set(value=lorentz1_amplitude, max=-0.01)
        params['l0_sigma'].set(value=lorentz1_sigma, min=stepsize/2,
                               max=full_width*4)
        params['l0_center'].set(value=lorentz1_center,
                                min=(x_axis[0])-n_steps*stepsize,
                                max=(x_axis[-1])+n_steps*stepsize)
        params['l1_amplitude'].set(value=lorentz0_amplitude, max=-0.01)
        params['l1_sigma'].set(value=lorentz0_sigma, min=stepsize/2,
                               max=full_width*4)
        params['l1_center'].set(value=lorentz0_center,
                                min=(x_axis[0])-n_steps*stepsize,
                                max=(x_axis[-1])+n_steps*stepsize)

    params['offset'].set(value=offset)

    result = mod.fit(data_noisy, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, data_noisy,'o', label='noisy data')
    plt.plot(x_axis, result.init_fit,'-y', label='initial fit')
    plt.plot(x_axis, result.best_fit,'-r', linewidth=2.0, label='actual fit')
    plt.plot(x_axis, data_smooth,'-g', label='smooth data')
    plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'b',label='original')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)

    plt.show()
#    print(result.fit_report()



def double_lorentzdip_testing2():
    """ Function to check the implemented double lorentz dip fit with offset. """
    start = 2800
    stop = 2950
    num_points = int((stop-start)/2)*1
    x = np.linspace(start, stop, num_points)

    x_nice = np.linspace(start, stop, num_points*4)

    mod,params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)
#    print('Parameters of the model',mod.param_names)

    p=Parameters()

    #============ Create data ==========

#                center=np.random.random(1)*50+2805
#            p.add('center',max=-1)
    p.add('l0_amplitude',value=-abs(np.random.random(1)*2+20))
    p.add('l0_center',value=np.random.random(1)*150.0+2800)
    p.add('l0_sigma',value=abs(np.random.random(1)*1.+1.))
    p.add('l1_center',value=np.random.random(1)*150.0+2800)
    p.add('l1_sigma',value=abs(np.random.random(1)*4.+1.))
    p.add('l1_amplitude',value=-abs(np.random.random(1)*1+10))

    p.add('offset',value=100.)

    data_noisy=(mod.eval(x=x,params=p)
                + 6*np.random.normal(size=x.shape))

    result = qudi_fitting.make_lorentziandouble_fit(x_axis=x, data=data_noisy,
                estimator=qudi_fitting.estimate_lorentziandouble_dip)

    data_smooth, offset = qudi_fitting.find_offset_parameter(x,data_noisy)

#                print('Offset:',offset)
#                print('Success:',result.success)
#                print(result.message)
#                print(result.lmdif_message)
#                print(result.fit_report(show_correl=False))

    data_level = data_smooth - offset


    plt.figure()
    plt.plot(x, data_noisy,'o', label='noisy data')
    plt.plot(x, result.init_fit,'-y', label='initial fit')
    plt.plot(x, result.best_fit,'-r', linewidth=2.0, label='actual fit')
    plt.plot(x, data_smooth,'-g', label='smooth data')
    plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'b',label='original')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)

    plt.show()
    print(result.fit_report())


def double_lorentzpeak_testing2():
    """ Function to check the implemented double lorentz peak fit with offset. """
    start = 2800
    stop = 2950
    num_points = int((stop-start)/2)*1
    x = np.linspace(start, stop, num_points)

    x_nice = np.linspace(start, stop, num_points*4)

    mod,params = qudi_fitting.make_multiplelorentzian_model(no_of_functions=2)
#    print('Parameters of the model',mod.param_names)

    p=Parameters()

    #============ Create data ==========

#                center=np.random.random(1)*50+2805
#            p.add('center',max=-1)
    p.add('l0_amplitude',value=abs(np.random.random(1)*2+20))
    p.add('l0_center',value=np.random.random(1)*150.0+2800)
    p.add('l0_sigma',value=abs(np.random.random(1)*1.+1.))
    p.add('l1_center',value=np.random.random(1)*150.0+2800)
    p.add('l1_sigma',value=abs(np.random.random(1)*4.+1.))
    p.add('l1_amplitude',value=abs(np.random.random(1)*1+10))

    p.add('offset',value=100.)

    data_noisy=(mod.eval(x=x,params=p)
                + 6*np.random.normal(size=x.shape))

#    data_noisy_inv = data_noisy*(-1)

    result = qudi_fitting.make_lorentziandouble_fit(x_axis=x, data=data_noisy,
                                                       estimator=qudi_fitting.estimate_lorentziandouble_peak)

    plt.figure()
    plt.plot(x, data_noisy,'o', label='noisy data')
    plt.plot(x, result.init_fit,'-y', label='initial fit')
    plt.plot(x, result.best_fit,'-r', linewidth=2.0, label='actual fit')
    plt.plot(x_nice, mod.eval(x=x_nice,params=result.params),'b',label='original')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=2, mode="expand", borderaxespad=0.)

    plt.show()
#    print(result.fit_report()


def double_lorentzian_fixedsplitting_testing():
    # This method does not work and has to be fixed!!!
    for ii in range(1):
#                time.sleep(0.51)
        start=2800
        stop=2950
        num_points=int((stop-start)/2)
        x = np.linspace(start, stop, num_points)

        mod,params = qudi_fitting.make_multiplelorentzian_model(no_of_lor=2)

        p=Parameters()

        #============ Create data ==========
        p.add('c',value=100)
        p.add('lorentz0_amplitude',value=-abs(np.random.random(1)*50+100))
        p.add('lorentz0_center',value=np.random.random(1)*150.0+2800)
        p.add('lorentz0_sigma',value=abs(np.random.random(1)*2.+1.))
        p.add('lorentz1_center',value=p['lorentz0_center']+20)
        p.add('lorentz1_sigma',value=abs(np.random.random(1)*2.+1.))
        p.add('lorentz1_amplitude',value=-abs(np.random.random(1)*50+100))

        data_noisy=(mod.eval(x=x,params=p)
                                + 2*np.random.normal(size=x.shape))

        para=Parameters()

        result=qudi_fitting.make_doublelorentzian_fit(axis=x,data=data_noisy,add_parameters=para)


        data_smooth, offset = qudi_fitting.find_offset_parameter(x,data_noisy)

        data_level=data_smooth-offset

        #search for double lorentzian

        error, \
        sigma0_argleft, dip0_arg, sigma0_argright, \
        sigma1_argleft, dip1_arg , sigma1_argright = \
        qudi_fitting._search_double_dip(x, data_level,make_prints=False)

        print(x[sigma0_argleft], x[dip0_arg], x[sigma0_argright], x[sigma1_argleft], x[dip1_arg], x[sigma1_argright])
        print(x[dip0_arg], x[dip1_arg])

        plt.plot((x[sigma0_argleft], x[sigma0_argleft]), ( data_noisy.min() ,data_noisy.max()), 'b-')
        plt.plot((x[sigma0_argright], x[sigma0_argright]), (data_noisy.min() ,data_noisy.max()), 'b-')

        plt.plot((x[sigma1_argleft], x[sigma1_argleft]), ( data_noisy.min() ,data_noisy.max()), 'k-')
        plt.plot((x[sigma1_argright], x[sigma1_argright]), ( data_noisy.min() ,data_noisy.max()), 'k-')

        try:
            plt.plot(x,data_noisy,'o')
            plt.plot(x,result.init_fit,'-y')
            plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
            plt.plot(x,data_smooth,'-g')
        except:
            print('exception')
        plt.show()

def lorentziandip_testing():
    """ Test the lorentzian estimator. """
    x_axis = np.linspace(800, 1000, 101)

    mod, params = qudi_fitting.make_lorentzian_model()
    print('Parameters of the model',mod.param_names)
    params = Parameters()

    params.add('amplitude',value=-20.)
    params.add('center',value=920.)
    params.add('sigma',value=5)
    params.add('offset', value=10.)

    data_nice = mod.eval(x=x_axis,params=params)
    data_noisy= data_nice + 6.0*np.random.normal(size=x_axis.shape)



#    gaus = gaussian(10,10)
#    gaus = 1
#    data_gauss_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum())
#    data_gauss_smooth = filters.convolve1d(data_noisy, gaus)
#    std_dev = 10
#    data_gauss_smooth = filters.gaussian_filter1d(data_noisy, std_dev)


    data_smooth, offset = qudi_fitting.find_offset_parameter(x_axis, data_noisy)
    print('offset',offset)

    plt.figure()
    plt.plot(x_axis, data_noisy, label='noisy data')
#    plt.plot(x_axis, data_gauss_smooth, label='gauss smooth data')
    plt.plot(x_axis, data_smooth, label='convoluted smooth data')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


#    offset = data_smooth.max()
#    offset = data_gauss_smooth.max()


#    data_level = data_gauss_smooth - offset
    data_level = data_smooth - offset
#    data_level = data_noisy - data_smooth.max()
#    data_level = data_noisy - offset

    amplitude = data_level.min()
    print('amplitude',amplitude)

    data_min = data_smooth.min()
    data_max = data_smooth.max()
    print('data_min',data_min)


    smoothing_spline = 1    # must be 1<= smoothing_spline <= 5
    function = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
    numerical_integral = abs(function.integral(x_axis[0], x_axis[-1]))

    if data_max > abs(data_min):
        qudi_fitting.log.warning('The lorentzian estimator set the peak to the minimal value, if '
                                 'you want to fit a peak instead of a dip rewrite the estimator.')

    amplitude_median = data_min
    x_zero = x_axis[np.argmin(data_smooth)]

    # For the fitting procedure it is much better to start with a larger sigma
    # then with a smaller one. A small sigma is prone to larger instabilities
    # in the fit.
    oversize_sigma = 1

    sigma = abs((numerical_integral*oversize_sigma) / (np.pi * amplitude_median))

    print('sigma', sigma)

#    amplitude = -1 *abs(amplitude_median * np.pi * sigma)

#    amplitude = data_min

    # auxiliary variables
    stepsize = x_axis[1]-x_axis[0]
    n_steps = len(x_axis)

    mod, params = qudi_fitting.make_lorentzian_model()

    params['amplitude'].set(value=amplitude, max=-1e-12)
    params['sigma'].set(value=sigma, min=stepsize/2,
                        max=(x_axis[-1]-x_axis[0])*10)
    params['center'].set(value=x_zero, min=(x_axis[0])-n_steps*stepsize,
                         max=(x_axis[-1])+n_steps*stepsize)
    params['offset'].set(value=offset)
#    para=Parameters()
#            para.add('sigma',value=p['sigma'].value)
#            para.add('amplitude',value=p['amplitude'].value)

#            result=mod.fit(data_noisy,x=x,params=p)
#    result=qudi_fitting.make_lorentzian_fit(x_axis=x, data=data_noisy, add_params=para)

    result = mod.fit(data_noisy, x=x_axis, params=params)
#            result=mod.fit(axis=x,data=data_noisy,add_parameters=p)

    print(result.fit_report())
#           gaussian filter
#    gaus=gaussian(10,10)
#    data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum())

#    print(result.init_values['offset'])
    plt.figure()
    plt.plot(x_axis, data_nice, label='ideal data')
    plt.plot(x_axis, data_noisy, label='noisy data')
    plt.plot(x_axis, result.init_fit, '-g', label='initial fit')
    plt.plot(x_axis, result.best_fit, '-r', label='actual fit')
    plt.plot(x_axis, data_smooth, '-y', label='smoothed data')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


def lorentziandip_testing2():
    """ Test the lorentzian fit directy with simulated data. """
    x_axis = np.linspace(800, 1000, 101)

    mod, params = qudi_fitting.make_lorentzian_model()
    print('Parameters of the model',mod.param_names)
    params = Parameters()

    params.add('amplitude',value=-10.)
    params.add('center',value=920.)
    params.add('sigma',value=5)
    params.add('offset', value=20.)

    data_nice = mod.eval(x=x_axis,params=params)
    data_noisy = data_nice + 2.0*np.random.normal(size=x_axis.shape)

    print(qudi_fitting.estimate_lorentzian_dip)


    result = qudi_fitting.make_lorentzian_fit(x_axis=x_axis, data=data_noisy, units=["MHz"], estimator = qudi_fitting.estimate_lorentzian_dip)

    plt.figure()
    plt.plot(x_axis, data_nice, label='ideal data')
    plt.plot(x_axis, data_noisy, label='noisy simulated data')
    plt.plot(x_axis, result.best_fit, '-r', label='actual fit')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())
    print(result.result_str_dict)


def lorentzianpeak_testing2():
    """ Test the lorentzian fit directy with simulated data. """
    x_axis = np.linspace(800, 1000, 101)

    mod, params = qudi_fitting.make_lorentzian_model()
    print('Parameters of the model',mod.param_names)
    params = Parameters()

    params.add('amplitude',value=10.)
    params.add('center',value=920.)
    params.add('sigma',value=5)
    params.add('offset', value=10.)

    data_nice = mod.eval(x=x_axis,params=params)
    data_noisy = data_nice + 5.0*np.random.normal(size=x_axis.shape)

    result = qudi_fitting.make_lorentzian_fit(x_axis=x_axis, data=data_noisy,
                                                 estimator=qudi_fitting.estimate_lorentzian_peak)

    plt.figure()
    plt.plot(x_axis, data_nice, label='ideal data')
    plt.plot(x_axis, data_noisy, label='noisy simulated data')
    plt.plot(x_axis, result.best_fit, '-r', label='actual fit')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

def compute_inv_dft(x_val, y_val, zeropad_num=0):
    """ Compute the inverse Discrete fourier Transform

    @param numpy.array x_val: 1D array
    @param numpy.array y_val: 1D array of same size as x_val
    @param int zeropad_num: zeropadding (adding zeros to the end of the array).
                            zeropad_num >= 0, the size of the array, which is
                            add to the end of the y_val before performing the
                            dft. The resulting array will have the length
                                (len(y_val)/2)*(zeropad_num+1)
                            Note that zeropadding will not change or add more
                            information to the dft, it will solely interpolate
                            between the dft_y values.

    @return: tuple(dft_x, dft_y):
                be aware that the return arrays' length depend on the zeropad
                number like
                    len(dft_x) = len(dft_y) = (len(y_val)/2)*(zeropad_num+1)


    """

    x_val = np.array(x_val)
    y_val = np.array(y_val)

    corrected_y = np.abs(y_val - y_val.max())
    # The absolute values contain the fourier transformed y values

#    zeropad_arr = np.zeros(len(corrected_y)*(zeropad_num+1))
#    zeropad_arr[:len(corrected_y)] = corrected_y
    fft_y = np.fft.ifft(corrected_y)

    # Due to the sampling theorem you can only identify frequencies at half
    # of the sample rate, therefore the FT contains an almost symmetric
    # spectrum (the asymmetry results from aliasing effects). Therefore take
    # the half of the values for the display.
    middle = int((len(corrected_y)+1)//2)

    # sample spacing of x_axis, if x is a time axis than it corresponds to a
    # timestep:
    x_spacing = np.round(x_val[-1] - x_val[-2], 12)

    # use the helper function of numpy to calculate the x_values for the
    # fourier space. That function will handle an occuring devision by 0:
    fft_x = np.fft.fftfreq(len(corrected_y), d=x_spacing)

#    return abs(fft_x[:middle]), fft_y[:middle]
    return fft_x[:middle], fft_y[:middle]
#    return fft_x, fft_y



def powerfluorescence_testing():
    x = np.linspace(1, 1000, 101)
    mod,params = qudi_fitting.make_powerfluorescence_model()
    print('Parameters of the model',mod.param_names,' with the independet variable',mod.independent_vars)

    params['I_saturation'].value=200.
    params['slope'].value=0.25
    params['intercept'].value=2.
    params['P_saturation'].value=100.
    data_noisy=(mod.eval(x=x,params=params)
                            + 10*np.random.normal(size=x.shape))

    para=dict()
    para['I_saturation']={"value":152.}
    para['slope']={"value":0.3,"vary":True}
    para['intercept']={"value":0.3,"vary":False,"min":0.}
    para['P_saturation']={"value":130.}
#    para.add('slope',value=0.3,vary=True)
#    para.add('intercept',value=0.3,vary=False,min=0.) #dark counts
#    para.add('P_saturation',value=130.   )


#            data=np.loadtxt('Po_Fl.txt')

    result=qudi_fitting.make_powerfluorescence_fit(x_axis=x, data=data_noisy, add_params=para)
#            result=qudi_fitting.make_powerfluorescence_fit(x_axis=data[:,0], data=data[:,2]/1000, add_paras=para)

    print(result.fit_report())

#            x_nice= np.linspace(0,data[:,0].max(), 101)

#            plt.plot(data[:,0],data[:,2]/1000,'ob')

    plt.plot(x,data_noisy,'-g')

    plt.plot(x,mod.eval(x=x,params=result.params),'-r')
    plt.show()

    print(result.message)

def double_gaussian_odmr_testing():
    """ DEPRECATED!!! WILL NOT WORK WITH THE CURRENT FIT IMPLEMENTATION!!!
    """
    for ii in range(1):

        start=2800
        stop=2950
        num_points=int((stop-start)/2)
        x = np.linspace(start, stop, num_points)

        mod,params = qudi_fitting.make_multiplelorentz_model(no_of_lor=2)
#            print('Parameters of the model',mod.param_names)

        p=Parameters()

        #============ Create data ==========

#                center=np.random.random(1)*50+2805
        p.add('lorentz0_amplitude',value=-abs(np.random.random(1)*50+100))
        p.add('lorentz0_center',value=np.random.random(1)*150.0+2800)
        p.add('lorentz0_sigma',value=abs(np.random.random(1)*2.+1.))
        p.add('lorentz1_center',value=np.random.random(1)*150.0+2800)
        p.add('lorentz1_sigma',value=abs(np.random.random(1)*2.+1.))
        p.add('lorentz1_amplitude',value=-abs(np.random.random(1)*50+100))
        p.add('c',value=100.)

        data_noisy=(mod.eval(x=x,params=p)
                                + 2*np.random.normal(size=x.shape))


        data_smooth, offset = qudi_fitting.find_offset_parameter(x,data_noisy)

        data_level=(data_smooth-offset)
#                set optimal thresholds
        threshold_fraction=0.4
        minimal_threshold=0.2
        sigma_threshold_fraction=0.3

        error, \
        sigma0_argleft, dip0_arg, sigma0_argright, \
        sigma1_argleft, dip1_arg , sigma1_argright = \
        qudi_fitting._search_double_dip(x, data_level,
                                threshold_fraction=threshold_fraction,
                                minimal_threshold=minimal_threshold,
                                sigma_threshold_fraction=sigma_threshold_fraction,
                                make_prints=False)

        print(x[sigma0_argleft], x[dip0_arg], x[sigma0_argright], x[sigma1_argleft], x[dip1_arg], x[sigma1_argright])
        print(x[dip0_arg], x[dip1_arg])

#                plt.plot((x[sigma0_argleft], x[sigma0_argleft]), ( data_level.min() ,data_level.max()), 'b-')
#                plt.plot((x[sigma0_argright], x[sigma0_argright]), (data_level.min() ,data_level.max()), 'b-')
#
#                plt.plot((x[sigma1_argleft], x[sigma1_argleft]), ( data_level.min() ,data_level.max()), 'k-')
#                plt.plot((x[sigma1_argright], x[sigma1_argright]), ( data_level.min() ,data_level.max()), 'k-')

        mod, params = qudi_fitting.make_multiplegaussian_model(no_of_gauss=2)

#                params['gaussian0_center'].value=x[dip0_arg]
#                params['gaussian0_center'].min=x.min()
#                params['gaussian0_center'].max=x.max()
#                params['gaussian1_center'].value=x[dip1_arg]
#                params['gaussian1_center'].min=x.min()
#                params['gaussian1_center'].max=x.max()



        result=qudi_fitting.make_doublegaussian_fit(x,data_noisy,
                                estimator='odmr_dip',
                                threshold_fraction=threshold_fraction,
                                minimal_threshold=minimal_threshold,
                                sigma_threshold_fraction=sigma_threshold_fraction)

#                plt.plot((result.init_values['gaussian0_center'], result.init_values['gaussian0_center']), ( data_level.min() ,data_level.max()), 'r-')
#                plt.plot((result.init_values['gaussian1_center'], result.init_values['gaussian1_center']), ( data_level.min() ,data_level.max()), 'r-')
#                print(result.init_values['gaussian0_center'],result.init_values['gaussian1_center'])

        print(result.fit_report())
#                print(result.message)
#                print(result.success)
        try:
#                    plt.plot(x, data_noisy, '-b')
            plt.plot(x, data_noisy, '-g')
#                    plt.plot(x, data_der*10, '-r')
#                    print(result.best_values['gaussian0_center']/1000,result.best_values['gaussian1_center']/1000)
            plt.plot(x,result.init_fit,'-y')
            plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
            plt.show()


        except:
            print('exception')


#
#                plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'-r')#
#                plt.show()
#
#                print('Peaks:',p['gaussian0_center'].value,p['gaussian1_center'].value)
#                print('Estimator:',result.init_values['gaussian0_center'],result.init_values['gaussian1_center'])
#
#                data=-1*data_smooth+data_smooth.max()
#                 print('peakutils',x[ peakutils.indexes(data, thres=1.1/max(data), min_dist=1)])
#                indices= peakutils.indexes(data, thres=5/max(data), min_dist=2)
#                print('Peakutils',x[indices])
#                pplot(x,data,indices)

def sine_testing():
    """ Sinus fit testing with a self defined estimator. """

    x_axis = np.linspace(0, 25, 75)
    x_axis1 = np.linspace(25, 50, 75)
    x_axis = np.append(x_axis, x_axis1)
    x_nice = np.linspace(x_axis[0],x_axis[-1], 1000)

    mod,params = qudi_fitting.make_sine_model()
    print('Parameters of the model',mod.param_names,
          ' with the independet variable',mod.independent_vars)

    print(1/(x_axis[1]-x_axis[0]))
    params['amplitude'].value=0.9 + np.random.normal(0,0.4)
    params['frequency'].value=0.1
#    params['frequency'].value=0.1+np.random.normal(0,0.5)
    params['phase'].value=np.pi*1.0
    params['offset'].value=3.94+np.random.normal(0,0.4)

    data_noisy=(mod.eval(x=x_axis,params=params)
                            + 0.3*np.random.normal(size=x_axis.shape))


    # set the offset as the average of the data
    offset = np.average(data_noisy)

    # level data
    data_level = data_noisy - offset

    # estimate amplitude
    ampl_val = max(np.abs(data_level.min()), np.abs(data_level.max()))

    # calculate dft with zeropadding to obtain nicer interpolation between the
    # appearing peaks.
    dft_x, dft_y = compute_ft(x_axis, data_level, zeropad_num=1)

    plt.figure()
    plt.plot(dft_x, dft_y, label='dft of data')
    plt.xlabel('Frequency')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    stepsize = x_axis[1]-x_axis[0]  # for frequency axis
    frequency_max = np.abs(dft_x[np.log(dft_y).argmax()])

    print(frequency_max)
    print('offset',offset)
#
    # find minimal distance to the next meas point in the corresponding time
    # value
    diff_array = np.ediff1d(x_axis)
    min_x_diff = diff_array.min()

    # if at least two identical values are in the array, then the difference is
    # of course zero, catch that case.
    for tries in range(len(diff_array)):
        if np.isclose(min_x_diff, 0.0):
            index = np.argmin(diff_array)
            diff_array = np.delete(diff_array, index)
            min_x_diff = diff_array.min()

        else:
            if len(diff_array) == 0:
                qudi_fitting.log.error('The passed x_axis for the sinus estimation contains the same values! Cannot do the fit!')

                return -1, params
            else:
                min_x_diff = diff_array.min()
            break

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data_level - func_val).sum()

    plt.figure()
    plt.plot(list(range(iter_steps)), sum_res, label='sum of different phase iteration')
    plt.xlabel('iteration')
    plt.ylabel('summed value')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # The minimum indicates where the sine function was fitting the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = sum_res.argmax()/iter_steps *2*np.pi - np.pi

    mod, params = qudi_fitting.make_sine_model()

    # values and bounds of initial parameters
    params['amplitude'].set(value=ampl_val)
    params['frequency'].set(value=frequency_max, min=0.0, max=1/(stepsize)*3)
    params['phase'].set(value=phase, min=-np.pi, max=np.pi)
    params['offset'].set(value=offset)

    # perform fit:
    result = mod.fit(data_noisy, x=x_axis, params=params)

#    plt.plot(x_nice,mod.eval(x=x_nice,params=params),'-g', label='nice data')
    plt.plot(x_axis,data_noisy,'ob', label='noisy data')
    plt.plot(x_axis,result.init_fit,'-y', label='initial values')
    plt.plot(x_axis,result.best_fit,'-r',linewidth=2.0, label='actual fit')
    #plt.plot(x_axis,np.gradient(data_noisy)+offset,'-g',linewidth=2.0,)
    plt.xlabel('time')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)

    plt.show()

#    print(result.fit_report())

def sine_testing2():
    """ Sinus fit testing with the direct fit method. """


    x_axis = np.linspace(0, 250, 75)
    x_axis1 = np.linspace(250, 500, 75)
    x_axis = np.append(x_axis, x_axis1)
    x_nice = np.linspace(x_axis[0],x_axis[-1], 1000)


    mod, params = qudi_fitting.make_sine_model()

    params['phase'].value = np.pi/2 # np.random.uniform()*2*np.pi
    params['frequency'].value = 0.01
    params['amplitude'].value = 1.5
    params['offset'].value = 0.4

    data = mod.eval(x=x_axis, params=params)
    data_noisy = (mod.eval(x=x_axis, params=params)
                  + 1.5* np.random.normal(size=x_axis.shape))

#    sorted_indices = x_axis.argsort()
#    x_axis = x_axis[sorted_indices]
#    data = data[sorted_indices]
#    diff_array = np.ediff1d(x_axis)
#    print(diff_array)
#    print(diff_array.min())
#    min_x_diff = diff_array.min()
#    if np.isclose(min_x_diff, 0.0):
#        index = np.argmin(diff_array)
#        print('index',index)
#        diff_array = np.delete(diff_array, index)
#        print('diff_array',diff_array)

    update_dict = {}
    update_dict['phase'] = {'vary': False, 'value': np.pi/2.}

    result = qudi_fitting.make_sine_fit(x_axis=x_axis, data=data_noisy,
                                              add_params=update_dict)


    plt.figure()
#    plt.plot(x_axis, data, 'simulate data')
    plt.plot(x_axis, data_noisy, label='noisy data')
    plt.plot(x_axis, result.init_fit, label='initial data')
    plt.plot(x_axis, result.best_fit, label='fit data')
    plt.xlabel('time')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


def sine_testing_data():
    """ Testing with read in data. """


    path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\2016\2016-10\2016-10-24_06_sensi_error_scaling_30min')
    filename = '20161024-18h52m42s_NV04_ddrive_0p65VD1_0p0975VD2_-43p15dBm_g_pi2_sensi_noise_rabiref_refD1_state_4.txt'

    meas_data = np.loadtxt(os.path.join(path, filename))
    x_axis = meas_data[0]
    data = meas_data[1]
    mod, params = qudi_fitting.make_sine_model()


    # level data
    offset = np.average(data)
    data_level = data - offset

    # estimate amplitude
    ampl_val = max(np.abs(data_level.min()), np.abs(data_level.max()))

    dft_x, dft_y = compute_ft(x_axis, data_level, zeropad_num=1)

    stepsize = x_axis[1]-x_axis[0]  # for frequency axis
#            freq = np.fft.fftfreq(data_level_zeropaded.size, stepsize)
#            frequency_max = dft_x[np.abs(fourier).argmax()]
    frequency_max = np.abs(dft_x[np.log(dft_y).argmax()])

    print("params['frequency'].value:", params['frequency'].value)
    print('np.round(frequency_max,3):', frequency_max)

    plt.figure()
#            plt.xlim(0,dft_x.max())
    plt.plot(dft_x[:int(len(dft_x)/2)],abs(dft_y)[:int(len(dft_x)/2)]**2)
#            plt.plot(dft_x,np.log(abs(dft_y)),'-r')
    plt.show()

     # find minimal distance to the next meas point in the corresponding time value>
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed
    #            convoluted time trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + (iter_s)/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data_level - func_val).sum()
#                sum_res[iter_s] = np.convolve(data_level, func_val, 'same').sum()

    plt.figure()
    plt.plot(sum_res)
    plt.show()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = sum_res.argmax()/iter_steps *2*np.pi - np.pi
#            phase = sum_res.argmin()/iter_steps *2*np.pi


    params['offset'].set(value=offset)
    params['amplitude'].set(value=ampl_val)
    params['frequency'].set(value=frequency_max, min=0.0, max=1/(stepsize)*3)
    params['phase'].set(value=phase, min=-np.pi, max=np.pi)

    result =mod.fit(data, x=x_axis, params=params)

#            result=qudi_fitting.make_sine_fit(axis=x_axis, data=data, add_parameters=None)

    plt.figure()
    #plt.plot(x_nice,mod.eval(x=x_nice,params=params),'-g', label='nice data')
    plt.plot(x_axis,data,'ob', label='noisy data')
    plt.plot(x_axis,result.init_fit,'-y', label='initial fit')
    plt.plot(x_axis,result.best_fit,'-r',linewidth=2.0, label='best fit')
    #plt.plot(x_axis,np.gradient(data_noisy)+offset,'-g',linewidth=2.0,)
    plt.xlabel('time')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)

    plt.show()

def twoD_gaussian_magnet():
    gmod,params = qudi_fitting.make_twoDgaussian_model()
    try:
        datafile=np.loadtxt(join(getcwd(),'ODMR_alignment.asc'),delimiter=',')
        data=datafile[1:,1:].flatten()
        y=datafile[1:,0]
        x=datafile[0,1:]
        xx, yy = np.meshgrid(x, y)
        axes=(xx.flatten(),yy.flatten())
    except:
        data = np.empty((121,1))
        amplitude=50
        x_zero=91+np.random.normal(0,0.4)
        y_zero=14+np.random.normal(0,0.4)
        sigma_x=0.4
        sigma_y=1
        offset=2820
        x = np.linspace(90,92,11)
        y = np.linspace(13,15,12)
        xx, yy = np.meshgrid(x, y)
        axes=(xx.flatten(),yy.flatten())
        theta_here= np.random.normal(0,100)/360.*(2*np.pi)
        gmod,params = qudi_fitting.make_twoDgaussian_model()
        data= gmod.eval(x=axes,amplitude=amplitude,x_zero=x_zero,
                        y_zero=y_zero,sigma_x=sigma_x,sigma_y=sigma_y,
                        theta=theta_here, offset=offset)
        data+=5*np.random.random_sample(np.shape(data))
        xx, yy = np.meshgrid(x, y)
        axes=(xx.flatten(),yy.flatten())

    para=dict()
    para["theta"]={"value":-0.15/np.pi,"vary":True}
    para["amplitude"]={"min":0.0,"max":100}
    para["offset"]={"min":0.0,"max":3000}
#    para.add('theta',value=-0.15/np.pi,vary=True)
#            para.add('x_zero',expr='0.5*y_zero')
#            para.add('sigma_x',value=0.05,vary=True )
#            para.add('sigma_y',value=0.3,vary=True )
#    para.add('amplitude',min=0.0, max= 100)
#    para.add('offset',min=0.0, max= 3000)
#            para.add('sigma_y',min=0.2*((15.-13.)/12.) , max=   10*(y[-1]-y[0]))
#            para.add('x_zero',value=40,min=50,max=100)

    result=qudi_fitting.make_twoDgaussian_fit(xy_axes=axes, data=data, add_parameters=para)
    print(result.params)

    print(result.fit_report())
    print('Maximum after fit (GHz): ',result.params['offset'].value+result.params['amplitude'].value)
#            FIXME: What does "Tolerance seems to be too small." mean in message?
#            print(result.message)
    plt.close('all')
    fig, ax = plt.subplots(1, 1)
    ax.hold(True)

    ax.imshow(result.data.reshape(len(y),len(x)),
              cmap=plt.cm.jet, origin='bottom', extent=(x.min(), x.max(),
                                       y.min(), y.max()),interpolation="nearest")
    ax.contour(x, y, result.best_fit.reshape(len(y),len(x)), 8
                , colors='w')
    plt.show()

#            print('Message:',result.message)

def poissonian_testing():
    start=0
    stop=30
    mu=8
    num_points=1000
    x = np.array(np.linspace(start, stop, num_points))
#            x = np.array(x,dtype=np.int64)
    mod,params = qudi_fitting.make_poissonian_model()
    print('Parameters of the model',mod.param_names)

    p=Parameters()
    p.add('mu',value=mu)
    p.add('amplitude',value=200.)

    data_noisy=(mod.eval(x=x,params=p) *
                np.array((1+0.001*np.random.normal(size=x.shape) *
                p['amplitude'].value ) ) )

    print('all int',all(isinstance(item, (np.int32,int, np.int64)) for item in x))
    print('int',isinstance(x[1], int),float(x[1]).is_integer())
    print(type(x[1]))
    #make the filter an extra function shared and usable for other functions
    gaus=gaussian(10,10)
    data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')


    result = qudi_fitting.make_poissonian_fit(x, data_noisy)
    print(result.fit_report())

    plt.figure()
    plt.plot(x, data_noisy, '-b', label='noisy data')
    plt.plot(x, data_smooth, '-g', label='smoothed data')
    plt.plot(x,result.init_fit,'-y', label='initial values')
    plt.plot(x,result.best_fit,'-r',linewidth=2.0, label='fit')
    plt.xlabel('counts')
    plt.ylabel('occurences')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

def double_poissonian_testing():
    """ Testing of double poissonian with self created data.
    First version of double poissonian fit."""

    start=100
    stop=300
    num_points=int((stop-start)+1)*100
    x = np.linspace(start, stop, num_points)

    # double poissonian
    mod,params = qudi_fitting.make_multiplepoissonian_model(no_of_functions=2)
    print('Parameters of the model',mod.param_names)
    parameter=Parameters()
    parameter.add('p0_mu',value=200)
    parameter.add('p1_mu',value=240)
    parameter.add('p0_amplitude',value=1)
    parameter.add('p1_amplitude',value=1)
    data_noisy = ( np.array(mod.eval(x=x,params=parameter)) *
                   np.array((1+0.2*np.random.normal(size=x.shape) )*
                   parameter['p1_amplitude'].value) )


    #make the filter an extra function shared and usable for other functions
    gaus=gaussian(10,10)
    data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')

    result = qudi_fitting.make_doublepoissonian_fit(x, data_noisy)
    print(result.fit_report())

    plt.figure()
    plt.plot(x, data_noisy, '-b', label='noisy data')
    plt.plot(x, data_smooth, '-g', label='smoothed data')
    plt.plot(x,result.init_fit,'-y', label='initial values')
    plt.plot(x,result.best_fit,'-r',linewidth=2.0, label='fit')
    plt.xlabel('counts')
    plt.ylabel('occurences')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()



def double_poissonian_testing_data():
    """ Double poissonian fit with read in data.
    Second version of double poissonian fit."""

    print_info = True

    # Usually, we have at first a data trace, from which we need to
    # obtain the histogram. You can just take any 1D trace for the
    # calculation!
    path = os.path.abspath(r'C:\Users\astark\Desktop\test_poisson\150902_21h58m_Rabi_171p0_micro-s_Trace.asc')
    trace_data = np.loadtxt(path)

    # Pretreatment of the data:

    # In the end, the fit should be almost independant of the bin width
    # in the histogram!
    bin_width = 1   # should be varied reasonably, i.e. always in
                    # multiples of 2 [1, 2, 4, 8, 16, ...]. The fit
                    # should be tested for all these binwidths!
    num_of_bins = int((trace_data.max() - trace_data.min())/bin_width)
    hist, bin_edges = np.histogram(trace_data, bins=num_of_bins)

    # the actual x-axis in the histogram must have one data point less
    # then the number of bin edges in the histogram
    x_axis = bin_edges[:-1]

    if print_info:
        print('hist',len(hist),'bin_edges',len(bin_edges))

    plt.figure()
    plt.plot(trace_data, label='Data trace')
    plt.xlabel('number of points in trace')
    plt.ylabel('counts')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()



    plt.figure()
    plt.plot(x_axis, hist, label='raw histogram with bin_width={0}'.format(bin_width))
    plt.xlabel('counts')
    plt.ylabel('occurences')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    # if you what to display the histogram in a nice way with matplotlib:
#            n, bins, patches = plt.hist(trace_data, num_of_bins)
#            n, bins, patches = plt.hist(trace_data, len(bin_edges)-1)
#            plt.show()


    # Create the model and parameter object of the double poissonian:
    mod_final, params = qudi_fitting.make_poissonian_model(no_of_functions=2)

    #TODO: make the filter an extra function shared and usable for
    #      other functions.
    # Calculate here also an interpolation factor, which will be based
    # on the given data set. If the convolution later on has more
    # points, then the fit has a higher chance to be successful.
    # The interpol_factor multiplies the number of points.
    if len(x_axis) < 20.:
        len_x = 5
        interpol_factor = 8
    elif len(x_axis) >= 100.:
        len_x = 10
        interpol_factor = 1
    else:
        if len(x_axis) < 60:
            interpol_factor = 4
        else:
            interpol_factor = 2
        len_x = int(len(x_axis) / 10.) + 1

    if print_info:
        print('interpol_factor', interpol_factor, 'len(x_axis)', len(x_axis))

    # Create the interpolation function, based on the data:
    function = InterpolatedUnivariateSpline(x_axis, hist, k=1)
    # adjust the x_axis to that:
    x_axis_interpol = np.linspace(x_axis[0],x_axis[-1],len(x_axis)*interpol_factor)
    # create actually the interpolated data:
    interpol_hist = function(x_axis_interpol)

    # Use a gaussian function to convolve with the data, to smooth the
    # datatrace. Then the peak search algorithm performs much better.
    gaus = gaussian(len_x, len_x)
    data_smooth = filters.convolve1d(interpol_hist, gaus / gaus.sum(), mode='mirror')

    # perform the peak search algorithm, use the peak search algorithm
    # which is also applied to the data, which had a dip.
    threshold_fraction=0.4
    minimal_threshold=0.1
    sigma_threshold_fraction=0.2

    search_res = qudi_fitting._search_double_dip(x_axis_interpol,
                                         data_smooth * (-1),
                                         threshold_fraction,
                                         minimal_threshold,
                                         sigma_threshold_fraction,
                                         make_prints=False)

    error = search_res[0]
    sigma0_argleft, dip0_arg, sigma0_argright = search_res[1:4]
    sigma1_argleft, dip1_arg, sigma1_argright = search_res[4:7]

    plt.figure()
    plt.plot(x_axis_interpol, data_smooth, label='smoothed data')
    plt.plot(x_axis_interpol, interpol_hist, label='interpolated data')
    plt.xlabel('counts')
    plt.ylabel('occurences')
    plt.axvline(x=x_axis_interpol[dip0_arg],color='r', label='left_peak_estimate')
    plt.axvline(x=x_axis_interpol[dip1_arg],color='m', label='right_peak_estimate')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    if print_info:
        print('search_res', search_res,
              'left_peak', x_axis_interpol[dip0_arg],
              'dip0_arg', dip0_arg,
              'right_peak', x_axis_interpol[dip1_arg],
              'dip1_arg', dip1_arg)


    # set the initial values for the fit:
    params['p0_mu'].value = x_axis_interpol[dip0_arg]
    params['p0_amplitude'].value = (interpol_hist[dip0_arg] / qudi_fitting.poisson(x_axis_interpol[dip0_arg], x_axis_interpol[dip0_arg]))

    params['p1_mu'].value = x_axis_interpol[dip1_arg]
    params['p1_amplitude'].value = ( interpol_hist[dip1_arg] / qudi_fitting.poisson(x_axis_interpol[dip1_arg], x_axis_interpol[dip1_arg]))

    # REMEMBER: the fit will be still performed on the original data!!!
    #           The previous treatment of the data was just to find the
    #           initial values!
    result = mod_final.fit(hist, x=x_axis, params=params)
    print(result.fit_report())

    # to total result in the end:
    plt.figure()
    plt.plot(x_axis, hist, '-b', label='original data')
    plt.plot(x_axis, data_smooth, '-g', linewidth=2.0, label='smoothed interpolated data')
    plt.plot(x_axis, result.init_fit,'-y', label='initial fit')
    plt.plot(x_axis, result.best_fit,'-r',linewidth=2.0, label='best fit')
    plt.xlabel('counts')
    plt.ylabel('occurences')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()



###############################################################################

def exponentialdecay_testing():
    """ Implementation of the estimator for exponential decay fitting. """

    x_axis = np.linspace(1, 51, 30)
    x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
    mod, params = qudi_fitting.make_decayexponential_model()
    print('Parameters of the model', mod.param_names,
          ' with the independet variable', mod.independent_vars)

    params['amplitude'].value = -100 + abs(np.random.normal(0,200))
    params['lifetime'].value = 1 + abs(np.random.normal(0,20))
    params['offset'].value = 1 + abs(np.random.normal(0, 200))
    print('\n', 'amplitude', params['amplitude'].value, '\n', 'lifetime',
              params['lifetime'].value,'\n', 'offset', params['offset'].value)

    data = mod.eval(x=x_axis, params=params)
    data_nice = mod.eval(x=x_nice, params=params)
    data_noisy = data + 5* np.random.normal(size=x_axis.shape)

    plt.figure()
    plt.plot(x_axis, data_noisy, 'ob', label='noisy data')
    plt.plot(x_nice, data_nice, '-g', label='nice data')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.,
               prop={'size':12})
    plt.show()

    # calculation of offset, take the last 10% from the end of the data
    # and perform the mean from those.
    offset = data_noisy[-max(1,int(len(x_axis)/10)):].mean()

    # substraction of offset, check whether amplitude is positive or negative
    if data_noisy[0] < data_noisy[-1]:
        data_level = offset - data_noisy
    else:
        data_level = data_noisy - offset

    # check if the data level contain still negative values and correct
    # the data level therefore. Otherwise problems in the logarithm appear.
    if data_level.min() <= 0:
        data_level = data_level - data_level.min()

    for i in range(0, len(x_axis)):
        if data_level[i] <= data_level.std():
            break
    print('Index stopped at "{0}" from total {1}'.format(i, len(x_axis)))

    # values and bound of parameter.
    ampl = data_noisy[-max(1, int(len(x_axis) / 10)):].std()
    min_lifetime = 2 * (x_axis[1] - x_axis[0])

    data_level_log = np.log(data_level[0:i])
    linear_result = qudi_fitting.make_linear_fit(
                        x_axis=x_axis[0:i],
                        data=data_level_log,
                        estimator=qudi_fitting.estimate_linear,
                        add_params=None)

    plt.figure()
    plt.plot(x_axis[0:i], data_level_log, 'ob', label='logarithmic data')
    plt.plot(x_axis[0:i], linear_result.best_fit,'-r', label='best fit')
    plt.plot(x_axis[0:i], linear_result.init_fit,'-y', label='initial value')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.,
               prop={'size':12}, title='linear fit results')
    plt.show()

    # make ready for fitting:
    mod, params = qudi_fitting.make_decayexponential_model()

    params['lifetime'].set(value=-1/linear_result.params['slope'].value, min=min_lifetime)
    # amplitude can be positive of negative
    if data[0] < data[-1]:
        params['amplitude'].set(value=-np.exp(linear_result.params['offset'].value), max=-ampl)
    else:
        params['amplitude'].set(value=np.exp(linear_result.params['offset'].value), min=ampl)

    params['offset'].set(value=offset)

    result = mod.fit(data_noisy, x=x_axis, params=params)


    plt.figure()
    plt.plot(x_axis, data_noisy, 'ob', label='noisy data')
    plt.plot(x_nice, data_nice, '-g', label='nice data')
    plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0, label='initial fit')
    plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0, label='actual fit')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.,
               prop={'size':12})
    plt.show()

    print(result.fit_report())


def exponentialdecay_testing2():
    """ Check the implemented estimator directly from fitlogic"""

    #generation of data for testing
    x_axis = np.linspace(1, 51, 20)
    x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
    mod, params = qudi_fitting.make_decayexponential_model()
    print('Parameters of the model', mod.param_names,
          ' with the independet variable', mod.independent_vars)

    params['amplitude'].value = -100 + abs(np.random.normal(0,200))
    params['lifetime'].value = 1 + abs(np.random.normal(0,20))
    params['offset'].value = 1 + abs(np.random.normal(0, 200))
    print('\n', 'amplitude', params['amplitude'].value, '\n', 'lifetime',
              params['lifetime'].value,'\n', 'offset', params['offset'].value)

    data = mod.eval(x=x_axis, params=params)
    data_nice = mod.eval(x=x_nice, params=params)
    data_noisy = data + 5* np.random.normal(size=x_axis.shape)

    # perform fit
    result = qudi_fitting.make_decayexponential_fit(
                x_axis=x_axis,
                data=data_noisy,
                estimator=qudi_fitting.estimate_decayexponential,
                add_params=None)

    plt.figure()
    plt.plot(x_axis, data_noisy, 'ob', label='noisy data')
    plt.plot(x_nice, data_nice, '-g', label='nice data')
    plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0, label='initial fit')
    plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0, label='actual fit')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.,
               prop={'size':12})
    plt.show()

    print(result.fit_report())
###########################################################################################
def bareexponentialdecay_testing():
    """ Implement the estimator for the bare exponential testing. """

    #generation of data for testing
    x_axis = np.linspace(1, 51, 20)
    x_nice = np.linspace(x_axis[0], x_axis[-1], 100)

    mod, params = qudi_fitting.make_bareexponentialdecay_model()
    print('Parameters of the model', mod.param_names,
          ' with the independet variable', mod.independent_vars)

    params['lifetime'].value = 1 + abs(np.random.normal(0,10))
    print('\n''lifetime', params['lifetime'].value)

    data_noisy = (mod.eval(x=x_axis, params=params)
                              + 0.125 * np.random.normal(size=x_axis.shape))
    data = abs(data_noisy)

    nice_data = mod.eval(x=x_nice, params=params)

    for i in range(0, len(x_axis)):
        if data[i] <= data.std():
            break

    print('Index stopped at "{0}" from total {1}'.format(i, len(x_axis)))

    offset = data_noisy.min()

    leveled_data = data_noisy - offset

    plt.figure()
    plt.plot(x_nice, nice_data, label='ref exp. decay data no offest')
    plt.plot(x_axis, data_noisy, 'o',  label='data noisy')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.,
               prop={'size':12}, title='ref nice data')
    plt.show()

    plt.figure()
    plt.plot(x_nice, np.log(nice_data), label='ref exp. decay data no offest, log')
    plt.plot(x_nice, np.log(nice_data+1), label='ref exp. decay data +1 offset, log')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.,
               prop={'size':12}, title='ref nice data, log')
    plt.show()


    data_log = np.log(leveled_data)

    linear_result = qudi_fitting.make_linear_fit(
                        x_axis=x_axis[0:i],
                        data=data_log[0:i],
                        estimator=qudi_fitting.estimate_linear,
                        add_params=None)

    plt.figure()
    plt.plot(x_axis, data_log, 'ob', label='logarithmic data')
    plt.plot(x_axis[0:i], linear_result.best_fit,'-r', label='best fit')
    plt.plot(x_axis[0:i], linear_result.init_fit,'-y', label='initial fit')
    plt.xlabel('Time x')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    mod, params = qudi_fitting.make_bareexponentialdecay_model()

    min_lifetime = 2 * (x_axis[1] - x_axis[0])
    params['lifetime'].set(value=-1/linear_result.params['slope'].value, min=min_lifetime)

    result = mod.fit(data_noisy, x=x_axis, params=params)
#
    plt.figure()
    plt.plot(x_axis, data_noisy, 'ob',label='noisy data')
    plt.plot(x_nice, nice_data, '-g', label='simulated data')
    plt.plot(x_axis, result.init_fit, '-y', linewidth=1.0, label='initial values')
    plt.plot(x_axis, result.best_fit, '-r', linewidth=1.0, label='best fit')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.xlabel('Time x')
    plt.ylabel('signal')
    plt.show()

#############################################################################################
def sineexponentialdecay_testing():
    # generation of data for testing
    x_axis = np.linspace(0, 100, 100)
    x_nice = np.linspace(x_axis[0], x_axis[-1], 1000)

    mod, params = qudi_fitting.make_sineexpdecaywithoutoffset_model()
    print('Parameters of the model', mod.param_names,
          ' with the independet variable', mod.independent_vars)

    params['amplitude'].value = abs(1 + abs(np.random.normal(0,4)))
    params['frequency'].value = abs(0.01 + abs(np.random.normal(0,0.2)))
    params['phase'].value = abs(np.random.normal(0,2*np.pi))
    params['offset'].value = 12 + np.random.normal(0,5)
    params['lifetime'].value = abs(0 + abs(np.random.normal(0,70)))
    print('\n', 'amplitude',params['amplitude'].value, '\n',
          'frequency',params['frequency'].value,'\n','phase',
          params['phase'].value, '\n','offset',params['offset'].value,
          '\n','lifetime', params['lifetime'].value)

    data_noisy = (mod.eval(x=x_axis, params=params)
                  + 0.5* np.random.normal(size=x_axis.shape))
    data = data_noisy
    offset = np.average(data)

    # level data
    data_level = data - offset

    # perform fourier transform with zeropadding to get higher resolution
    data_level_zeropaded = np.zeros(int(len(data_level) * 2))
    data_level_zeropaded[:len(data_level)] = data_level
    fourier = np.fft.fft(data_level_zeropaded)
    stepsize = x_axis[1] - x_axis[0]  # for frequency axis
    freq = np.fft.fftfreq(data_level_zeropaded.size, stepsize)
    fourier_power = (fourier * fourier.conj()).real


    plt.plot(freq[:int(len(freq) / 2)],
              fourier_power[:int(len(freq) / 2)], '-or')
    plt.xlim(0, 0.5)
    plt.show()





    result = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis,
                                                        data=data_noisy,
                                                        add_parameters=None)
    plt.plot(x_axis, data_noisy, 'o--b')
    plt.plot(x_nice,mod.eval(x=x_nice, params=params),'-g')
    print(result.fit_report())
    plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0, )
    plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0, )
    #plt.plot(x_axis, np.gradient(data_noisy) + offset, '-g', linewidth=2.0, )

    plt.show()

    units = dict()
    units['frequency'] = 'GHz'
    units['phase'] = 'rad'
    #nits['offset'] = 'arb. u.'
    units['amplitude']='arb. u.'
    print(qudi_fitting.create_fit_string(result, mod, units))

def sineexponentialdecay_testing_data():
    """ With read in data and seld.  """
    path = os.path.abspath(r'C:\Users\astark\Desktop\decaysine')

    filename = '2016-10-19_FID_3MHz_Rabi_5micro-spulsed.txt'

    path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\2016\2016-11\2016-11-06_04_ddrive_signal_-35p19_-61p15dBm_ana')
    filename = '20161106-21h31m38s_NV04_ddrive_0p65VD1_0p0975VD2_-35p19_-61p15dBm_g_1ms_meas_7.txt'

    meas_data = np.loadtxt(os.path.join(path, filename))
    x_axis = meas_data[0]
    data = meas_data[1]

    mod, params = qudi_fitting.make_sineexpdecaywithoutoffset_model()

    offset = np.mean(data)

    # level data
    data_level = data - offset

    # estimate amplitude
    # estimate amplitude
    ampl_val = max(np.abs(data_level.min()),np.abs(data_level.max()))

    dft_x, dft_y = compute_ft(x_axis, data_level, zeropad_num=1)

    stepsize = x_axis[1] - x_axis[0]  # for frequency axis

    frequency_max = np.abs(dft_x[dft_y.argmax()])

    params['frequency'].set(value=frequency_max,
                            min=min(0.1 / (x_axis[-1]-x_axis[0]),dft_x[3]),
                            max=min(0.5 / stepsize, dft_x.max()-abs(dft_x[2]-dft_x[0])))


    #remove noise
    a = np.std(dft_y)
    for i in range(0, len(dft_x)):
        if dft_y[i]<=a:
            dft_y[i] = 0

    #calculating the width of the FT peak for the estimation of lifetime
    s = 0
    for i in range(0, len(dft_x)):
        s+= dft_y[i]*abs(dft_x[1]-dft_x[0])/max(dft_y)
    params['lifetime'].set(value=0.5/s)


    # find minimal distance to the next meas point in the corresponding time value>
    min_x_diff = np.ediff1d(x_axis).min()

    # How many points are used to sample the estimated frequency with min_x_diff:
    iter_steps = int(1/(frequency_max*min_x_diff))
    if iter_steps < 1:
        iter_steps = 1

    sum_res = np.zeros(iter_steps)

    # Procedure: Create sin waves with different phases and perform a summation.
    #            The sum shows how well the sine was fitting to the actual data.
    #            The best fitting sine should be a maximum of the summed time
    #            trace.

    for iter_s in range(iter_steps):
        func_val = ampl_val * np.sin(2*np.pi*frequency_max*x_axis + iter_s/iter_steps *2*np.pi)
        sum_res[iter_s] = np.abs(data_level - func_val).sum()

    # The minimum indicates where the sine function was fittng the worst,
    # therefore subtract pi. This will also ensure that the estimated phase will
    # be in the interval [-pi,pi].
    phase = (sum_res.argmax()/iter_steps *2*np.pi - np.pi )%(2*np.pi)

    print('phase:', phase)

    plt.figure()
    plt.plot(sum_res)
    plt.show()

    # values and bounds of initial parameters
    params['amplitude'].set(value=ampl_val, min=0)
    params['phase'].set(value=phase, min=-2*np.pi, max=2*np.pi)
    params['offset'].set(value=offset)
    params['lifetime'].set(min=2 *(x_axis[1]-x_axis[0]),
                           max = 1/(abs(dft_x[1]-dft_x[0])*0.5) )


    result = mod.fit(data, x=x_axis, params=params)


    plt.figure()
    plt.plot(x_axis/65000, data, label='measured data')
    plt.plot(x_axis/65000, result.best_fit,'-g', label='fit')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

    print(params.pretty_print)

def sineexponentialdecay_testing_data2():
    """ With read in data.  """
    path = os.path.abspath(r'C:\Users\astark\Desktop\decaysine')

    filename = '2016-10-19_FID_3MHz_Rabi_5micro-spulsed.txt'

    path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\2016\2016-11\2016-11-04_02_sdrive_signal_-49p15_-61p15dBm_ana')
    filename = '20161104-18h03m52s_NV04_sdrive_0p65VD1_-49p15_-61p15dBm_g_0p5ms_meas_state_0.txt'


    meas_data = np.loadtxt(os.path.join(path, filename))
    x_axis = meas_data[0]
    data = meas_data[1]

    mod, params = qudi_fitting.make_sineexponentialdecay_model()

    result = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data)

    plt.figure()
    plt.plot(x_axis/65000, data, label='measured data')
    plt.plot(x_axis/65000, result.best_fit,'-g', label='fit')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

##################################################################################################################
def stretchedexponentialdecay_testing():
    x_axis = np.linspace(0, 51, 100)
    x_nice = np.linspace(x_axis[0], x_axis[-1], 100)

    mod, params = qudi_fitting.make_stretchedexponentialdecay_model()
    print('Parameters of the model', mod.param_names,
          ' with the independet variable', mod.independent_vars)

    params['beta'].value = 2 + abs(np.random.normal(0,0.5))
    params['amplitude'].value = 10 #- abs(np.random.normal(0,20))
    params['lifetime'].value =1 + abs(np.random.normal(0,30))
    params['offset'].value = 1 + abs(np.random.normal(0, 20))
    print('\n', 'amplitude', params['amplitude'].value, '\n', 'lifetime',
          params['lifetime'].value,'\n', 'offset', params['offset'].value,'\n',
          'beta', params['beta'].value)

    data_noisy = (mod.eval(x=x_axis, params=params)
                  + 1.5* np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_stretchedexponentialdecay_fit(axis=x_axis,
                                                     data=data_noisy,
                                                     add_parameters=None)

    data = data_noisy
    #calculation of offset
    offset = data[-max(1,int(len(x_axis)/10)):].mean()
    if data[0]<data[-1]:
        params['amplitude'].max = 0-data.std()
        data_sub = offset - data
    else:
        params['amplitude'].min = data.std()
        data_sub = data-offset

    amplitude = data_sub.max()-data_sub[-max(1,int(len(x_axis)/10)):].mean()-data_sub[-max(1,int(len(x_axis)/10)):].std()
    data_level = data_sub/amplitude

    a = 0
    b = len(data_sub)
    for i in range(0,len(data_sub)):
        if data_level[i]>=1:
            a=i+1
        if data_level[i] <=data_level.std():
            b=i
            break
    print(a,b)

    try:
        double_lg_data = np.log(-np.log(data_level[a:b]))

        #linear fit, see linearmethods.py
        X=np.log(x_axis[a:b])
        linear_result = qudi_fitting.make_linear_fit(axis=X, data=double_lg_data,
                                             add_parameters= None)
        print(linear_result.params)
        plt.plot(np.log(x_axis),np.log(-np.log(data_level)),'ob')
        plt.plot(np.log(x_axis[a:b]),linear_result.best_fit,'-r')
        plt.plot(np.log(x_axis[a:b]),linear_result.init_fit,'-y')
        print(linear_result.fit_report())
        plt.show()
    except:
        print("except")




    plt.plot(x_axis, data_noisy, 'ob')
    plt.plot(x_nice, mod.eval(x=x_nice, params=params), '-g')
    print(result.fit_report())
    plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0)
    plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0)
    #plt.plot(x_axis, np.gradient(data_noisy), '-g', linewidth=2.0, )
    plt.show()

def stretched_sine_exponential_decay_testing_data():
    """ With read in data.  """

    path = os.path.abspath(r'C:\Users\astark\Desktop\gausssinedecay')
    filename = '20161027-18h15m52s_NV04_ddrive_0p65VD1_0p0975VD2_-43p15dBm_g_pi2_decay_rabiref_refD2_state.txt'

    meas_data = np.loadtxt(os.path.join(path, filename))
    x_axis = meas_data[0]/65000
    data = meas_data[1]

    result = qudi_fitting.make_sinestretchedexponentialdecay_fit(x_axis=x_axis,
                                                                 data=data)

    plt.figure()
    plt.plot(x_axis, data, label='measured data')
    plt.plot(x_axis, result.best_fit,'-g', label='fit')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())



###############################################################################
def linear_testing():
    x_axis = np.linspace(1, 51, 100)
    x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
    mod, params = qudi_fitting.make_linear_model()
    print('Parameters of the model', mod.param_names, ' with the independet variable', mod.independent_vars)

    params['slope'].value = 2  # + abs(np.random.normal(0,1))
    params['offset'].value = 50 #+ abs(np.random.normal(0, 200))
    #print('\n', 'beta', params['beta'].value, '\n', 'lifetime',
          #params['lifetime'].value)
    data_noisy = (mod.eval(x=x_axis, params=params)
                  + 10 * np.random.normal(size=x_axis.shape))

    result = qudi_fitting.make_linear_fit(axis=x_axis, data=data_noisy, add_parameters=None)
    plt.plot(x_axis, data_noisy, 'ob')
    plt.plot(x_nice, mod.eval(x=x_nice, params=params), '-g')
    print(result.fit_report())
    plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0)
    plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0)

    plt.show()

def fit_data():
    data=np.loadtxt('data.dat')
    print(data)
    params = dict()
    params["c"] = {"min" : -np.inf,"max" : np.inf}
    result = qudi_fitting.make_lorentzian_fit(axis=data[:,0], data=data[:,3], add_parameters=params)
    print(result.fit_report())
    plt.plot(data[:,0],-data[:,3]+2,"b-o",label="data mean")
#    plt.plot(data[:,0],data[:,1],label="data")
#    plt.plot(data[:,0],data[:,2],label="data")
    plt.plot(data[:,0],-result.best_fit+2,"r-",linewidth=2.,label="fit")
#    plt.plot(data[:,0],result.init_fit,label="init")
    plt.xlabel("time (ns)")
    plt.ylabel("polarization transfer (arb. u.)")
    plt.legend(loc=1)
#    plt.savefig("pol20_24repetition_pol.pdf")
#    plt.savefig("pol20_24repetition_pol.png")
    plt.show()
    savedata=[[data[ii,0],-data[ii,3]+2,-result.best_fit[ii]+2] for ii in range(len(data[:,0]))]
    np.savetxt("pol_data_fit.csv",savedata)
#    print(result.params)

    print(result.params)


def double_exponential_testing():
    """Testing for simulated data for a double exponential decay with offset."""

    x_axis = np.linspace(5, 350,200)
    lifetime = 100
    ampl = -6
    offset = -4
    data = ampl * np.exp(-(x_axis/lifetime)**2) +offset


    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*0.3

    plt.figure()
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    std_dev =10
    data_smoothed = filters.gaussian_filter1d(noisy_data, std_dev)


    # calculation of offset, take the last 10% from the end of the data
    # and perform the mean from those.
    offset = data_smoothed[-max(1, int(len(x_axis)/10)):].mean()

    # substraction of offset, check whether
    if data_smoothed[0] < data_smoothed[-1]:
        data_smoothed = offset - data_smoothed
        inv=-1
    else:
        data_smoothed = data_smoothed - offset
        inv=1

    if data_smoothed.min() <= 0:
        data_smoothed = data_smoothed - data_smoothed.min()


    plt.figure()
    plt.plot(x_axis, data_smoothed, label='data smoothed')
#    plt.plot(x_axis, noisy_data, label='noisy_data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    for i in range(0, len(x_axis)):
        if data_smoothed[i] <= data_smoothed.std():
            break

    print('data_smoothed.std():',data_smoothed.std())

    data_level_log = np.log(data_smoothed[0:i])

    p= np.polyfit(x_axis[0:i], data_level_log, deg=2)
    lifetime = 1/np.sqrt(abs(p[0]))
    print('lifetime:', lifetime )

    amplitude = np.exp(p[2])

    print('amplitude_poly:', amplitude )

    poly = np.poly1d(p)

    plt.figure()
    plt.plot(x_axis[0:i], data_level_log, label='data smoothed filtered')
    plt.plot(x_axis[0:i], poly(x_axis[0:i]), label='2.nd degree polynomial fit')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    mod, params = qudi_fitting.make_doubleexponentialdecayoffset_model()

    params['amplitude'].set(value=amplitude*inv)
    params['offset'].set(value=offset)

    min_lifetime = 2 * (x_axis[1]-x_axis[0])
    params['lifetime'].set(value=lifetime, min=min_lifetime)

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(result.fit_report())


def double_exponential_testing2():
    """Testing for simulated data for a double exponential decay with offset."""

    x_axis = np.linspace(5, 350,200)
    lifetime = 100
    ampl = 0.2
    offset = 0
    data = ampl * np.exp(-(x_axis/lifetime)**2) +offset


    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*0.3

    res = qudi_fitting.make_doubleexponentialdecayoffset_fit(x_axis=x_axis,
                                                             data=noisy_data)

    plt.figure()
    plt.plot(x_axis, res.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(res.fit_report())
    return


def stretched_exponential_decay_testing():
    """ Testing for simuated data for a streched exponential decay. """


    x_axis = np.linspace(5, 350,200)
    lifetime = 150
    ampl = 0.2
    offset = 1
    beta = 4
    data = ampl * np.exp(-(x_axis/lifetime)**beta) +offset


    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*0.05

    res = qudi_fitting.make_stretchedexponentialdecayoffset_fit(x_axis=x_axis,
                                                             data=noisy_data)

    plt.figure()
    plt.plot(x_axis, res.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()
    print(res.fit_report())
    return

def two_sine_offset_testing():
    """ Testing procedure for the estimator for a double sine with offset fit. """

    x_axis = np.linspace(5, 300 ,200)
    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 1
    freq1 = 0.02

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 1
    freq2 = 0.01

    offset = 1

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) +ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*2


    res = qudi_fitting.make_sine_fit(x_axis=x_axis, data=noisy_data)


    data_sub = noisy_data - res.best_fit

    res2 = qudi_fitting.make_sine_fit(x_axis=x_axis, data=data_sub)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, res.best_fit+res2.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    mod, params = qudi_fitting.make_sinedouble_model()

    params['s1_amplitude'].set(value=res.params['amplitude'].value)
    params['s1_frequency'].set(value=res.params['frequency'].value)
    params['s1_phase'].set(value=res.params['phase'].value)

    params['s2_amplitude'].set(value=res2.params['amplitude'].value)
    params['s2_frequency'].set(value=res2.params['frequency'].value)
    params['s2_phase'].set(value=res2.params['phase'].value)

    params['offset'].set(value=data.mean())

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print("freq1:", result.params['s1frequency'].value)
    print("freq2:", result.params['s2frequency'].value)


def two_sine_offset_testing2():
    """ Testing procedure for the implemented two sine with exponential
        decay and offset fit. """

    x_axis = np.linspace(5, 300 ,200)
    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 1
    freq1 = 0.02

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 1
    freq2 = 0.01

    offset = 1

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) +ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*1.0

    result = qudi_fitting.make_sinedouble_fit(x_axis=x_axis, data=noisy_data)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

def two_sine_exp_decay_offset_testing():
    """ Testing procedure for the implemented two sine with exponential decay
        and offset fit. """

    x_axis = np.linspace(5, 600 ,200)
    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 1
    freq1 = 0.011

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    offset = 1
    lifetime = 100

    data = (ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) +ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2))*np.exp(-(x_axis/lifetime)) + offset
    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*0.6


    result1 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=noisy_data)
    data_sub = noisy_data - result1.best_fit

    result2 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data_sub)

    mod, params = qudi_fitting.make_sinedoublewithexpdecay_model()

    # Fill the parameter dict:
    params['s1_amplitude'].set(value=result1.params['amplitude'].value)
    params['s1_frequency'].set(value=result1.params['frequency'].value)
    params['s1_phase'].set(value=result1.params['phase'].value)

    params['s2_amplitude'].set(value=result2.params['amplitude'].value)
    params['s2_frequency'].set(value=result2.params['frequency'].value)
    params['s2_phase'].set(value=result2.params['phase'].value)

    lifetime = (result1.params['lifetime'].value + result2.params['lifetime'].value)/2
    params['lifetime'].set(value=lifetime, min=2*(x_axis[1]-x_axis[0]))
    params['offset'].set(value=data.mean())

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
#    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print("freq1:", result.params['s1_frequency'].value)
    print("freq2:", result.params['s2_frequency'].value)

    print(result.fit_report())


def two_sine_exp_decay_offset_testing2():
    """ Testing procedure for the implemented two sine with offset fit. """

    x_axis = np.linspace(5, 600 ,200)
    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 0.11
    freq1 = 0.02

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 1
    freq2 = 0.01

    offset = 1
    lifetime = 100

    data = (ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) +ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2))*np.exp(-(x_axis/lifetime)) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*0.2

    result = qudi_fitting.make_sinedoublewithexpdecay_fit(x_axis=x_axis, data=noisy_data)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())


def two_sine_two_exp_decay_offset_testing():
    """ Testing procedure for the implemented two sine two exponential decay
        with offset fit. """

    x_axis = np.linspace(5, 600 ,200)
    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 1
    freq1 = 0.02

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 3
    freq2 = 0.01

    offset = 1
    lifetime1 = 100
    lifetime2 = 100

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1)*np.exp(-(x_axis/lifetime1))  +ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2)*np.exp(-(x_axis/lifetime2)) + offset
    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*0.5


    result1 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=noisy_data)
    data_sub = noisy_data - result1.best_fit

    result2 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data_sub)

    plt.figure()
    plt.plot(x_axis, data_sub,'-', label='sub')
#    plt.plot(x_axis, result1.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, '-', label='noisy_data')
#    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    mod, params = qudi_fitting.make_sinedoublewithtwoexpdecay_model()

    # Fill the parameter dict:
    params['e1_amplitude'].set(value=result1.params['amplitude'].value)
    params['e1_frequency'].set(value=result1.params['frequency'].value)
    params['e1_phase'].set(value=result1.params['phase'].value)
    params['e1_lifetime'].set(value=result1.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))


    params['e2_amplitude'].set(value=result2.params['amplitude'].value)
    params['e2_frequency'].set(value=result2.params['frequency'].value)
    params['e2_phase'].set(value=result2.params['phase'].value)
    params['e2_lifetime'].set(value=result2.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['offset'].set(value=data.mean())

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print("freq1:", result.params['e1_frequency'].value)
    print("freq2:", result.params['e2_frequency'].value)

    print(result.fit_report())

def two_sine_two_exp_decay_offset_testing2():
    """ Testing procedure for the implemented two sine with offset fit. """

    x_axis = np.linspace(5, 400 ,200)
    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 2
    freq1 = 0.02

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 1
    freq2 = 0.01

    offset = 1
    lifetime1 = 100
    lifetime2 = 200

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1)*np.exp(-(x_axis/lifetime1))  +ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2)*np.exp(-(x_axis/lifetime2)) + offset
    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*1

    result = qudi_fitting.make_sinedoublewithtwoexpdecay_fit(x_axis=x_axis, data=noisy_data, estimator=qudi_fitting.estimate_sinedoublewithtwoexpdecay)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

def three_sine_offset_testing():
    """ Testing procedure for the estimator for a three sine with offset fit. """

    x_axis = np.linspace(5, 300 ,200)

    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 3
    freq1 = 0.03

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    phase3 = np.random.uniform()*2*np.pi
    ampl3 = 1
    freq3 = 0.05

    offset = 1.1

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) + ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) + ampl3 * np.sin(2*np.pi*freq3*x_axis +phase3) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*3

    x_dft1, y_dft1 = compute_ft(x_val=x_axis, y_val=noisy_data, zeropad_num=1)

    plt.figure()
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time (micro-s)')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    res1 = qudi_fitting.make_sine_fit(x_axis=x_axis, data=noisy_data)
    data_sub1 = noisy_data - res1.best_fit

    x_dft2, y_dft2 = compute_ft(x_val=x_axis, y_val=data_sub1, zeropad_num=1)

    res2 = qudi_fitting.make_sine_fit(x_axis=x_axis, data=data_sub1)
    data_sub2 = data_sub1 - res2.best_fit

    res3 = qudi_fitting.make_sine_fit(x_axis=x_axis, data=data_sub2)

    x_dft3, y_dft3 = compute_ft(x_val=x_axis, y_val=data_sub2, zeropad_num=1)

    plt.figure()
    plt.plot(x_dft1, y_dft1, '-', label='noisy_data (3 peaks)')
    plt.plot(x_dft2, y_dft2, '-', label='noisy_data (2 peaks)')
    plt.plot(x_dft3, y_dft3, '-', label='noisy_data (1 peak)')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    mod, params = qudi_fitting.make_sinetriple_model()

    params['s1_amplitude'].set(value=res1.params['amplitude'].value)
    params['s1_frequency'].set(value=res1.params['frequency'].value)
    params['s1_phase'].set(value=res1.params['phase'].value)

    params['s2_amplitude'].set(value=res2.params['amplitude'].value)
    params['s2_frequency'].set(value=res2.params['frequency'].value)
    params['s2_phase'].set(value=res2.params['phase'].value)

    params['s3_amplitude'].set(value=res3.params['amplitude'].value)
    params['s3_frequency'].set(value=res3.params['frequency'].value)
    params['s3_phase'].set(value=res3.params['phase'].value)

    params['offset'].set(value=data.mean())

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())


def three_sine_offset_testing2():
    """ Testing procedure for the implemented three sine with offset fit. """

    x_axis = np.linspace(5, 300 ,200)

    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 3
    freq1 = 0.03

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    phase3 = np.random.uniform()*2*np.pi
    ampl3 = 1
    freq3 = 0.05

    offset = 1.1

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) + ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) + ampl3 * np.sin(2*np.pi*freq3*x_axis +phase3) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*3

    result = qudi_fitting.make_sinetriple_fit(x_axis=x_axis, data=noisy_data)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

def three_sine_exp_decay_offset_testing():
    """ Testing procedure for the estimator for a three sine with exponential
        decay and with offset fit. """

    x_axis = np.linspace(5, 300 ,200)

    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 3
    freq1 = 0.03

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    phase3 = np.random.uniform()*2*np.pi
    ampl3 = 1
    freq3 = 0.05

    lifetime = 100
    offset = 1.1

    data = (ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) + ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) + ampl3 * np.sin(2*np.pi*freq3*x_axis +phase3))*np.exp(-(x_axis/lifetime)) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*1

    x_dft1, y_dft1 = compute_ft(x_val=x_axis, y_val=noisy_data, zeropad_num=1)

    plt.figure()
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time (micro-s)')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    res1 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=noisy_data)
    data_sub1 = noisy_data - res1.best_fit

    x_dft2, y_dft2 = compute_ft(x_val=x_axis, y_val=data_sub1, zeropad_num=1)

    res2 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data_sub1)
    data_sub2 = data_sub1 - res2.best_fit

    res3 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data_sub2)

    x_dft3, y_dft3 = compute_ft(x_val=x_axis, y_val=data_sub2, zeropad_num=1)

    plt.figure()
    plt.plot(x_dft1, y_dft1, '-', label='noisy_data (3 peaks)')
    plt.plot(x_dft2, y_dft2, '-', label='noisy_data (2 peaks)')
    plt.plot(x_dft3, y_dft3, '-', label='noisy_data (1 peak)')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    mod, params = qudi_fitting.make_sinetriplewithexpdecay_model()

    params['s1_amplitude'].set(value=res1.params['amplitude'].value)
    params['s1_frequency'].set(value=res1.params['frequency'].value)
    params['s1_phase'].set(value=res1.params['phase'].value)

    params['s2_amplitude'].set(value=res2.params['amplitude'].value)
    params['s2_frequency'].set(value=res2.params['frequency'].value)
    params['s2_phase'].set(value=res2.params['phase'].value)

    params['s3_amplitude'].set(value=res3.params['amplitude'].value)
    params['s3_frequency'].set(value=res3.params['frequency'].value)
    params['s3_phase'].set(value=res3.params['phase'].value)

    lifetime = (res1.params['lifetime'].value + res2.params['lifetime'].value + res3.params['lifetime'].value)/3
    params['lifetime'].set(value=lifetime,
                           min=2*(x_axis[1]-x_axis[0]))
    params['offset'].set(value=data.mean())

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())


def three_sine_exp_decay_offset_testing2():
    """ Testing procedure for the implemented three sine with exponential
        decay and offset fit. """

    x_axis = np.linspace(5, 300 ,200)

    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 3
    freq1 = 0.03

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    phase3 = np.random.uniform()*2*np.pi
    ampl3 = 2
    freq3 = 0.05

    lifetime = 100
    offset = 1.1

    data = (ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) + ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) + ampl3 * np.sin(2*np.pi*freq3*x_axis +phase3))*np.exp(-(x_axis/lifetime)) + offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*1

    result = qudi_fitting.make_sinetriplewithexpdecay_fit(x_axis=x_axis, data=noisy_data)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())


def three_sine_three_exp_decay_offset_testing():
    """ Testing procedure for the estimator for a three sine with three
        exponential decays and with offset fit. """

    x_axis = np.linspace(5, 300 ,200)

    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 3
    freq1 = 0.03

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    phase3 = np.random.uniform()*2*np.pi
    ampl3 = 1
    freq3 = 0.05

    lifetime1 = 100
    lifetime2 = 150
    lifetime3 = 200
    offset = 1.1

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) * np.exp(-(x_axis/lifetime1)) + \
           ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) * np.exp(-(x_axis/lifetime2)) + \
           ampl3 * np.sin(2*np.pi*freq3*x_axis +phase3) * np.exp(-(x_axis/lifetime3)) + \
           offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*1

    x_dft1, y_dft1 = compute_ft(x_val=x_axis, y_val=noisy_data, zeropad_num=1)

    plt.figure()
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time (micro-s)')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    res1 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=noisy_data)
    data_sub1 = noisy_data - res1.best_fit

    x_dft2, y_dft2 = compute_ft(x_val=x_axis, y_val=data_sub1, zeropad_num=1)

    res2 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data_sub1)
    data_sub2 = data_sub1 - res2.best_fit

    res3 = qudi_fitting.make_sineexponentialdecay_fit(x_axis=x_axis, data=data_sub2)

    x_dft3, y_dft3 = compute_ft(x_val=x_axis, y_val=data_sub2, zeropad_num=1)

    plt.figure()
    plt.plot(x_dft1, y_dft1, '-', label='noisy_data (3 peaks)')
    plt.plot(x_dft2, y_dft2, '-', label='noisy_data (2 peaks)')
    plt.plot(x_dft3, y_dft3, '-', label='noisy_data (1 peak)')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    mod, params = qudi_fitting.make_sinetriplewiththreeexpdecay_model()

    params['e1_amplitude'].set(value=res1.params['amplitude'].value)
    params['e1_frequency'].set(value=res1.params['frequency'].value)
    params['e1_phase'].set(value=res1.params['phase'].value)
    params['e1_lifetime'].set(value=res1.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['e2_amplitude'].set(value=res2.params['amplitude'].value)
    params['e2_frequency'].set(value=res2.params['frequency'].value)
    params['e2_phase'].set(value=res2.params['phase'].value)
    params['e2_lifetime'].set(value=res2.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['e3_amplitude'].set(value=res3.params['amplitude'].value)
    params['e3_frequency'].set(value=res3.params['frequency'].value)
    params['e3_phase'].set(value=res3.params['phase'].value)
    params['e3_lifetime'].set(value=res3.params['lifetime'].value,
                              min=2*(x_axis[1]-x_axis[0]))

    params['offset'].set(value=data.mean())

    result = mod.fit(noisy_data, x=x_axis, params=params)

    plt.figure()
#    plt.plot(x_axis, data_sub,'-', label='sub')
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())

def three_sine_three_exp_decay_offset_testing2():
    """ Testing procedure for the implemented three sine with three
        exponential decay and offset fit. """

    x_axis = np.linspace(5, 300 ,200)

    phase1 = np.random.uniform()*2*np.pi
    ampl1 = 3
    freq1 = 0.03

    phase2 = np.random.uniform()*2*np.pi
    ampl2 = 2
    freq2 = 0.01

    phase3 = np.random.uniform()*2*np.pi
    ampl3 = 1
    freq3 = 0.05

    lifetime1 = 120
    lifetime2 = 150
    lifetime3 = 50
    offset = 1.1

    data = ampl1 * np.sin(2*np.pi*freq1*x_axis +phase1) * np.exp(-(x_axis/lifetime1)) + \
           ampl2 * np.sin(2*np.pi*freq2*x_axis +phase2) * np.exp(-(x_axis/lifetime2)) + \
           ampl3 * np.sin(2*np.pi*freq3*x_axis +phase3) * np.exp(-(x_axis/lifetime3)) + \
           offset

    noisy_data = data + data.mean() * np.random.normal(size=x_axis.shape)*1.2

    result = qudi_fitting.make_sinetriplewiththreeexpdecay_fit(x_axis=x_axis, data=noisy_data)

    plt.figure()
    plt.plot(x_axis, result.best_fit,'-', label='fit')
    plt.plot(x_axis, noisy_data, 'o--', label='noisy_data')
    plt.plot(x_axis, data,'-', label='ideal data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()

    print(result.fit_report())


def voigt_testing():

    x_axis = np.linspace(800, 1000, 301)

    mod, params = qudi_fitting.make_lorentzian_model()
    p=Parameters()

    params.add('amplitude',value=30.)
    params.add('center',value=920.)
    params.add('sigma',value=10)
    params.add('c',value=10.)

    data_noisy = (mod.eval(x=x_axis, params=params)
                            + 0.2*np.random.normal(size=x_axis.shape))

    para=Parameters()
#            para.add('sigma',value=p['sigma'].value)
#            para.add('amplitude',value=p['amplitude'].value)

    voigt_mod = models.VoigtModel()

    plt.figure()
    plt.plot(x_axis, data_noisy, label='measured data')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()


    error, amplitude, x_zero, sigma, offset = qudi_fitting.estimate_lorentzpeak(x_axis, data_noisy)

#    data_noisy = data_noisy - data_noisy.min()

#    params = voigt_mod.make_params()
    params = mod.make_params()

    # auxiliary variables
    stepsize = x_axis[1]-x_axis[0]
    n_steps = len(x_axis)

    if x_axis[1]-x_axis[0] > 0:

        params['amplitude'].set(value=amplitude, vary=True, min=2e-12,
                                max=np.inf)
        params['sigma'].set(value=sigma, vary=True, min=(x_axis[1]-x_axis[0])/2,
                            max=(x_axis[-1]-x_axis[0])*10)
        params['center'].set(value=amplitude, vary=True,
                             min=(x_axis[0])-n_steps*stepsize,
                             max=(x_axis[-1])+n_steps*stepsize)

    if x_axis[0]-x_axis[1] > 0:

        params['amplitude'].set(value=amplitude, vary=True, min=2e-12,
                                max=np.inf)
        params['sigma'].set(value=sigma, vary=True, min=(x_axis[0]-x_axis[1])/2,
                            max=(x_axis[0]-x_axis[1])*10)
        params['center'].set(value=amplitude, vary=True,
                             min=x_axis[-1],
                             max=x_axis[0])


    result = mod.fit(data_noisy, x=x_axis, params=params)
#    result = voigt_mod.fit(data_noisy, x=x_axis, params=params)

    plt.figure()
    plt.plot(x_axis, data_noisy, label='measured data')
    plt.plot(x_axis, result.best_fit, label='fit')
    plt.xlabel('Time micro-s')
    plt.ylabel('signal')
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
               ncol=2, mode="expand", borderaxespad=0.)
    plt.show()




plt.rcParams['figure.figsize'] = (10,5)

if __name__ == "__main__":

#    gaussianpeak_testing()
#    gaussianpeak_testing2()
#    gaussiandip_testing2()
#    gaussianlinearoffset_testing()
#    gaussianlinearoffset_testing2()
#    gaussianlinearoffset_testing_data()
#    two_gaussian_peak_testing()
#    two_gaussian_peak_testing2()
#    two_gaussian_dip_testing2()
#    gaussian_twoD_testing()
#    double_gaussian_odmr_testing()

#    lorentziandip_testing()
#    lorentziandip_testing2()
#    lorentzianpeak_testing2()

#    double_lorentzdip_testing()
#    double_lorentzdip_testing2()
#    double_lorentzpeak_testing2()
#    double_lorentzian_fixedsplitting_testing()
#    N14_testing()
#    N14_testing2()
#    N14_testing_data()
#    N14_testing_data2()
#    N15_testing()
#    N15_testing2()
#    powerfluorescence_testing()
#    sine_testing()
#    sine_testing2()
#    sine_testing_data() # needs a selected file for data input
#    twoD_gaussian_magnet()
#    poissonian_testing()
#    double_poissonian_testing()
#    double_poissonian_testing_data() # needs a selected file for data input
    bareexponentialdecay_testing()
#    exponentialdecay_testing()
#    exponentialdecay_testing2()
#
#    sineexponentialdecay_testing()
#    sineexponentialdecay_testing_data() # needs a selected file for data input
#    sineexponentialdecay_testing_data2() # use the estimator from the fitlogic,
                                          # needs a selected file for data input



#    stretched_sine_exponential_decay_testing_data() # needs a selected file for data input
#    linear_testing()
#    double_exponential_testing()
#    double_exponential_testing2()
#    stretched_exponential_decay_testing()
#    two_sine_offset_testing()
#    two_sine_offset_testing2()
#    two_sine_exp_decay_offset_testing()
#    two_sine_exp_decay_offset_testing2()
#    two_sine_two_exp_decay_offset_testing()
#    two_sine_two_exp_decay_offset_testing2()
#    three_sine_offset_testing()
#    three_sine_offset_testing2()
#    three_sine_exp_decay_offset_testing()
#    three_sine_exp_decay_offset_testing2()
#    three_sine_three_exp_decay_offset_testing()
#    three_sine_three_exp_decay_offset_testing2()


#    voigt_testing()

