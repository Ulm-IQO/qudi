# -*- coding: utf-8 -*-
"""
This file contains a test bed for implementation of new fit
functions and estimators. Here one can also do stability checks
 with dummy data. This is a playground so no conventions have to be
 taken into account. This is completely standalone and does not interact with
 qudi. It only will import the fitting methods from qudi.

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

Copyright (c) 2015-2016 Jochen Scheuer jochen.scheuer@uni-ulm.de
Copyright (c) 2016 Ou Wang ou.wang@uni-ulm.de

"""

import numpy as np
import sys
import scipy.optimize as opt
from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.interpolate import splrep, sproot, splev
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel,LinearModel
from lmfit import Parameters
import scipy
import matplotlib
import matplotlib.pylab as plt
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import time
import random
import importlib
from os import listdir,getcwd
from os.path import isfile, join
import os

from scipy import special
from scipy.special import gammaln as gamln
import statsmodels.api as sm
#import peakutils
#from peakutils.plot import plot as pplot

#matplotlib.rcParams.update({'font.size': 12})

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
        def __init__(self):

            filenames=[]

            # get from this script the absolte filepath:
            file_path = os.path.realpath(__file__)

            # retrieve the path to the directory of the file:
            script_dir_path = os.path.dirname(file_path)

            # retrieve the path to the directory of the qudi module:
            mod_path = os.path.dirname(script_dir_path)

            fitmodules_path = join(mod_path,'logic','fitmethods')

            if fitmodules_path not in sys.path:
                sys.path.append(fitmodules_path)

            for f in listdir(fitmodules_path):
                if isfile(join(fitmodules_path, f)):
                    filenames.append(f[:-3])

            oneD_fit_methods = dict()
            twoD_fit_methods = dict()

            for files in filenames:

                mod = importlib.import_module('{}'.format(files))
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
                        self.logMsg('It was not possible to import element {} into FitLogic.'.format(method),
                                msgType='error')
            try:
                self.logMsg('Methods were included to FitLogic, but only if naming is right: ',
                            'make_<own method>_fit. If estimator should be added, the name has',
                                    msgType='message')
            except:
                pass


##############################################################################
##############################################################################

                        #Testing routines

##############################################################################
##############################################################################

        def N15_testing(self):
            x = np.linspace(2840, 2860, 101)*1e6

            mod,params = self.make_multiplelorentzian_model(no_of_lor=2)
#            print('Parameters of the model',mod.param_names)

            p=Parameters()

            p.add('lorentz0_amplitude',value=-3e7)
            p.add('lorentz0_center',value=2850*1e6+abs(np.random.random(1)*8)*1e6)
#            p.add('lorentz0_sigma',value=abs(np.random.random(1)*1)*1e6+0.5*1e6)
            p.add('lorentz0_sigma',value=0.5*1e6)
            p.add('lorentz1_amplitude',value=p['lorentz0_amplitude'].value)
            p.add('lorentz1_center',value=p['lorentz0_center'].value+3.03*1e6)
            p.add('lorentz1_sigma',value=p['lorentz0_sigma'].value)
            p.add('c',value=100.)

            data_noisy=(mod.eval(x=x,params=p)
                                    + 1.5*np.random.normal(size=x.shape))

            data_smooth_lorentz, offset = self.find_offset_parameter(x, data_noisy)


            hf_splitting = 3.03 * 1e6 # Hz
            #filter should always have a length of approx linewidth 1MHz
            points_within_1MHz = len(x)/(x.max()-x.min()) * 1e6
            # filter should have a width of 4 MHz
            x_filter = np.linspace(0,4*points_within_1MHz,4*points_within_1MHz)
            lorentz = np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/4),
                                            (x_filter >= len(x_filter)/4)*(x_filter<len(x_filter)*3/4),
                                            (x_filter >= len(x_filter)*3/4)], [1, 0,1])

            # if the filter is smaller than 5 points a convolution does not make sense
            if len(lorentz) >= 3:
                data_convolved = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(),
                                             mode='constant', cval=data_smooth_lorentz.max())
                x_axis_min = x[data_convolved.argmin()]-hf_splitting
                plt.plot(x,data_convolved,'-g')

            else:
                x_axis_min = x[data_smooth_lorentz.argmin()]-hf_splitting

            result=self.make_N15_fit(x,data_noisy)
            print(result.best_values['lorentz0_center'])
            plt.plot(x,data_noisy)
            plt.plot(x,result.init_fit,'-y')
            plt.plot(x,result.best_fit,'-r')
            plt.show()

        def N14_testing(self):
            # x = np.linspace(2800, 2900, 51)
            # x = np.linspace(2820, 2920, 1001)*1e6
            x = np.linspace(2850, 2860, 101)*1e6

            path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\2016\2016-07\2016-07-05 N14 fit fails\20160705-1203-10_n14_fit_fails_80MHz_span_ODMR_data.dat')
            data = np.loadtxt(path)

            x=data[:,0]
            data_noisy = data[:,1]


            mod, params = self.make_multiplelorentzian_model(no_of_lor=3)
#            print('Parameters of the model',mod.param_names)

#            data_smooth_lorentz, offset=self.find_offset_parameter(x, data)
            data_smooth_lorentz, offset = self.find_offset_parameter(x, data_noisy)

            #filter of one dip should always have a length of approx linewidth 1MHz
            points_within_1MHz = len(x)/(x.max()-x.min()) * 1e6
            # filter should have a width of 5MHz
            x_filter = np.linspace(0, 5*points_within_1MHz, 5*points_within_1MHz)
            lorentz = np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/5),
                                            (x_filter >= len(x_filter)/5)*(x_filter<len(x_filter)*2/5),
                                            (x_filter >= len(x_filter)*2/5)*(x_filter<len(x_filter)*3/5),
                                            (x_filter >= len(x_filter)*3/5)*(x_filter<len(x_filter)*4/5),
                                            (x_filter >= len(x_filter)*4/5)], [1, 0,1,0,1])

            # if the filter is smaller than 5 points a convolution does not make sense
            if len(lorentz) >= 5:
                data_convolved = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(), mode='constant', cval=data_smooth_lorentz.max())
                x_axis_min = x[data_convolved.argmin()]-2.15*1e6
            else:
                x_axis_min = x[data_smooth_lorentz.argmin()]-2.15*1e6

#            p.add('lorentz0_amplitude',value=-1e9)
##            p.add('lorentz0_center',value=2850+abs(np.random.random(1)*8))
#            p.add('lorentz0_center',value=2852*1e6)
##            p.add('lorentz0_sigma',value=abs(np.random.random(1)*1)+0.5)
#            p.add('lorentz0_sigma',value=1*1e6)
#            p.add('lorentz1_amplitude',value=p['lorentz0_amplitude'].value)
#            p.add('lorentz1_center',value=p['lorentz0_center'].value+2.15*1e6)
#            p.add('lorentz1_sigma',value=p['lorentz0_sigma'].value)
#            p.add('lorentz2_amplitude',value=p['lorentz0_amplitude'].value)
#            p.add('lorentz2_center',value=p['lorentz1_center'].value+2.15*1e6)
#            p.add('lorentz2_sigma',value=p['lorentz0_sigma'].value)
#            p.add('c',value=15000.)

            # level of the data, that means the offset is subtracted and the
            # real data are present
            data_level = data_smooth_lorentz - data_smooth_lorentz.mean()
            minimum_level = data_level.min()


            # plt.figure(1)
#            plt.plot(x, data_smooth_lorentz)
            plt.plot(x, data_level)
            plt.show()

            # integral of data corresponds to sqrt(2) * Amplitude * Sigma
            function = InterpolatedUnivariateSpline(x, data_level, k=1)
            Integral = function.integral(x[0], x[-1])

#            lorentz0_sigma = abs(Integral /
#                                 (np.pi * amplitude) )
#
#            lorentz0_amplitude = -1*abs(amplitude*np.pi*lorentz0_sigma)

#            minimum_level = 36500

            sigma = abs(Integral /(minimum_level/np.pi ) )
#            sigma = 600000

            amplitude = -1*abs(minimum_level*np.pi*sigma)
#            amplitude = -3000000000

#            amplitude = 1800
            print('amplitude', amplitude, 'sigma', sigma)

            # Since the total amplitude of the lorentzian is depending on sigma
            # it makes sense to vary sigma within an interval, which is smaller
            # than the minimal distance between two points. Then the fit
            # algorithm will have a larger range to determine the amplitude
            # properly. That is the main issue with the fit.
            linewidth = sigma
            minimal_linewidth = (x[1]-x[0])/4
            maximal_linewidth = x[-1]-x[0]
            print('minimal_linewidth',minimal_linewidth, 'maximal_linewidth', maximal_linewidth)


            p = Parameters()

                    #            (Name,                  Value,          Vary, Min,             Max,           Expr)
            p.add('lorentz0_amplitude', value=amplitude,   vary=True,                                                max=-1e-6)
            p.add('lorentz0_center',    value=x_axis_min)
            p.add('lorentz0_sigma',     value=linewidth,                           min=minimal_linewidth, max=maximal_linewidth)
            p.add('lorentz1_amplitude', value=p['lorentz0_amplitude'].value,    vary=True,                  max=-1e-6)
            p.add('lorentz1_center',    value=p['lorentz0_center'].value+2.15*1e6,                                     expr='lorentz0_center+2.15*1e6')
            p.add('lorentz1_sigma',     value=p['lorentz0_sigma'].value,   min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
            p.add('lorentz2_amplitude', value=p['lorentz0_amplitude'].value,    vary=True,                  max=-1e-6)
            p.add('lorentz2_center',    value=p['lorentz1_center'].value+2.15*1e6,                                      expr='lorentz0_center+4.3*1e6')
            p.add('lorentz2_sigma',     value=p['lorentz0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
            p.add('c',                  value=np.mean(data_smooth_lorentz))


            data_test = mod.eval(x=x,params=p)


            # create a genera dictionary of dicts which each parameter name will
            # be assigned to an attribute name:
            param_dict = dict()
            for single_param in p:
                store_param = dict()
                if p[single_param].min is not None:
                    store_param['min'] = p[single_param].min
                if p[single_param].min is not None:
                    store_param['max'] = p[single_param].max
                if p[single_param].min is not None:
                    store_param['vary'] = p[single_param].vary
                if p[single_param].min is not None:
                    store_param['value'] = p[single_param].value
                if p[single_param].min is not None:
                    store_param['expr'] = p[single_param].expr

                param_dict[single_param] = store_param

            result2 = mod.fit(data_noisy,x=x, params=p)

            result=self.make_N14_fit(x, data_noisy, param_dict)

            print(result.fit_report())

            data_smooth_lorentz, offset=self.find_offset_parameter(x,data_noisy)
#
            stepsize_in_x=len(x)/(x.max()-x.min())*1e6
            print('stepsize_in_x',stepsize_in_x)
            print('x.min()', x.min(),'x.max()', x.max())
#            stepsize_in_x=

#            lorentz = np.ones(int(stepsize_in_x)+1)
            x_filter = np.linspace(0,5*stepsize_in_x,5*stepsize_in_x)
            lorentz = np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/5),
                                            (x_filter >= len(x_filter)/5)*(x_filter<len(x_filter)*2/5),
                                            (x_filter >= len(x_filter)*2/5)*(x_filter<len(x_filter)*3/5),
                                            (x_filter >= len(x_filter)*3/5)*(x_filter<len(x_filter)*4/5),
                                            (x_filter >= len(x_filter)*4/5)], [1, 0,1,0,1])

#            print(lorentz)
#             plt.figure(2)
            plt.plot(x_filter/5, lorentz)
            plt.axis([-0.5, 5.5, -0.05, 1.05])
            plt.show()

#            print(x[int(len(lorentz)/5)]-x[0])

#            data_smooth = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(), mode='constant', cval=data_smooth_lorentz.max())
#            print(offset)
            data_level = data_smooth_lorentz - data_smooth_lorentz.max()

            # plt.figure(3)
            plt.plot(data_level)
            plt.show()

            amplitude = data_level.min()
                # integral of data corresponds to sqrt(2) * Amplitude * Sigma
            x_axis = x
            function = InterpolatedUnivariateSpline(x_axis, data_level, k=1)
            Integral = function.integral(x_axis[0], x_axis[-1])
            print('Integral',Integral)
#
            lorentz0_sigma = abs(Integral /
                                 (np.pi * amplitude) )

            lorentz0_amplitude = -1*abs(amplitude*np.pi*lorentz0_sigma)


            print('lorentz0_sigma/3.',lorentz0_sigma/3., ',lorentz0_amplitude/3.',lorentz0_amplitude/3.)
#
#            numerical_integral_1=numerical_integral_0
#
#            lorentz1_sigma = abs( numerical_integral_1
#                                  / (np.pi * lorentz1_amplitude)  )
#
#            #esstimate amplitude
#            lorentz1_amplitude = -1*abs(lorentz1_amplitude*np.pi*lorentz1_sigma)

            plt.plot(x,data_noisy,'-b', label='data')
#            plt.plot(x,data_smooth_lorentz,'-g',linewidth=2.0)
#            plt.plot(x,data_smooth,'-y',linewidth=2.0)
            plt.plot(x,result.init_fit,'-y')
#            plt.plot(x,result.best_fit,'-r', label='fit')
#            plt.plot(x,result.init_fit,'-g',label='init')
            plt.plot(x, data_test,'-k', label='test')
            plt.plot(x, result2.best_fit,'-r', label='fit')
            plt.show()


        def N14_testing2(self):

            # Create/load data for fitting
            # ============================

            path = os.path.abspath(r'C:\Users\astark\Dropbox\Doctorwork\2016\2016-07\2016-07-05 N14 fit fails\20160705-1147-41_n14_fit_fails_60MHz_span_ODMR_data.dat')
            data = np.loadtxt(path)

            # The data for the fit:
            x_axis = data[:,0]
            data_noisy = data[:,1]

            # get the model of the three lorentzian peak, this gives you the
            # ability to get the used parameter container for the fit.
            mod, params = self.make_multiplelorentzian_model(no_of_lor=3)


            # Estimate the initial parameters
            # ===============================

            # find the offset parameter, which should be in the fit the zero
            # level.
            data_smooth_lorentz, offset = self.find_offset_parameter(x_axis, data_noisy)

            offset_array = np.zeros(len(x_axis))+offset

            # plot all the current results:
            plt.plot(x_axis, data_smooth_lorentz)
            plt.plot(x_axis, data_noisy)
            plt.plot(x_axis, offset_array)
            plt.show()

            # filter of one dip should always have a length of approx linewidth 1MHz
            points_within_1MHz = len(x_axis)/(x_axis.max()-x_axis.min()) * 1e6
            print(points_within_1MHz)

            # filter should have a width of 5MHz
            x_filter = np.linspace(0, 5*points_within_1MHz, 5*points_within_1MHz)
            lorentz = np.piecewise(x_filter, [(x_filter >= 0)                   * (x_filter < len(x_filter)*1/5),
                                              (x_filter >= len(x_filter)*1/5)   * (x_filter < len(x_filter)*2/5),
                                              (x_filter >= len(x_filter)*2/5)   * (x_filter < len(x_filter)*3/5),
                                              (x_filter >= len(x_filter)*3/5)   * (x_filter < len(x_filter)*4/5),
                                              (x_filter >= len(x_filter)*4/5)],
                                   [1, 0, 1, 0, 1])

            plt.plot(x_filter, lorentz)
            plt.show()
            print('offset', offset)

            # if the filter is smaller than 5 points a convolution does not
            # make sense
            if len(lorentz) >= 5:

                # perform a convolution of the data
                data_convolved = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(), mode='constant', cval=data_smooth_lorentz.max())
                x_axis_min = x_axis[data_convolved.argmin()]-2.15*1e6
            else:
                x_axis_min = x_axis[data_smooth_lorentz.argmin()]-2.15*1e6


            plt.plot(x_axis, data_smooth_lorentz)
#            plt.plot(x_axis, data_noisy)
#            plt.plot(x_axis, offset_array)
            plt.plot(x_axis, data_convolved)
            plt.show()
            print('x_axis_min', x_axis_min)

            # Create the parameter container, with the estimated values, which
            # should be passed to the fit algorithm
            parameters = Parameters()

            data_level = data_smooth_lorentz - data_smooth_lorentz.max()
            minimum_level = data_level.min()

            # In order to perform a smooth integral to obtain the area under
            # the curve make an interpolation of the passed data, in case they
            # are very sparse. That increases the accuracy of the calculated
            # Integral.
            # integral of data corresponds to sqrt(2) * Amplitude * Sigma

            smoothing_spline = 1 # must be 1<= smoothing_spline <= 5
            interpol_func = InterpolatedUnivariateSpline(x_axis, data_level, k=smoothing_spline)
            Integral = interpol_func.integral(x_axis[0], x_axis[-1])

            # set the number of interpolated points
            num_int_points = 1000
            x_interpolated_values = np.linspace(x_axis.min(), x_axis.max(), num_int_points)

            # and use now the interpolate function to generate the data.
#            plt.plot(x_interpolated_values, interpol_func(x_interpolated_values))
#            plt.plot(x_axis, data_level)
#            plt.show()


            sigma = abs(Integral /(np.pi * minimum_level) )

            amplitude = -1*abs(minimum_level*np.pi*sigma)

            linewidth = sigma
            minimal_linewidth = x_axis[1]-x_axis[0]
            maximal_linewidth = x_axis[-1]-x_axis[0]

            #            (Name,                  Value,          Vary, Min,             Max,           Expr)
            parameters.add('lorentz0_amplitude', value=amplitude,                                                  max=-1e-6)
            parameters.add('lorentz0_center',    value=x_axis_min)
            parameters.add('lorentz0_sigma',     value=linewidth,                           min=minimal_linewidth, max=maximal_linewidth)
            parameters.add('lorentz1_amplitude', value=parameters['lorentz0_amplitude'].value,                     max=-1e-6)
            parameters.add('lorentz1_center',    value=parameters['lorentz0_center'].value+2.15*1e6,                                      expr='lorentz0_center+2.15*1e6')
            parameters.add('lorentz1_sigma',     value=parameters['lorentz0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
            parameters.add('lorentz2_amplitude', value=parameters['lorentz0_amplitude'].value,                     max=-1e-6)
            parameters.add('lorentz2_center',    value=parameters['lorentz1_center'].value+2.15*1e6,                                      expr='lorentz0_center+4.3*1e6')
            parameters.add('lorentz2_sigma',     value=parameters['lorentz0_sigma'].value,  min=minimal_linewidth, max=maximal_linewidth, expr='lorentz0_sigma')
            parameters.add('c',                  value=data_smooth_lorentz.max())





        def twoD_testing(self):
            data = np.empty((121,1))
            amplitude=np.random.normal(3e5,1e5)
            x_zero=91+np.random.normal(0,0.8)
            y_zero=14+np.random.normal(0,0.8)
            sigma_x=np.random.normal(0.7,0.2)
            sigma_y=np.random.normal(0.7,0.2)
            offset=0
            x = np.linspace(90,92,11)
            y = np.linspace(13,15,12)
            xx, yy = np.meshgrid(x, y)

            axes=(xx.flatten(),yy.flatten())

            theta_here=10./360.*(2*np.pi)

#            data=self.twoD_gaussian_function((xx,yy),*(amplitude,x_zero,y_zero,sigma_x,sigma_y,theta_here,offset))
            gmod,params = self.make_twoDgaussian_model()

            data= gmod.eval(x=axes,amplitude=amplitude,x_zero=x_zero,y_zero=y_zero,sigma_x=sigma_x,sigma_y=sigma_y,theta=theta_here, offset=offset)
            data+=50000*np.random.random_sample(np.shape(data))

            gmod,params = self.make_twoDgaussian_model()

            para=Parameters()
#            para.add('theta',vary=False)
#            para.add('x_zero',expr='0.5*y_zero')
#            para.add('sigma_x',min=0.2*((92.-90.)/11.) ,           max=   10*(x[-1]-y[0]) )
#            para.add('sigma_y',min=0.2*((15.-13.)/12.) ,           max=   10*(y[-1]-y[0]))
#            para.add('x_zero',value=40,min=50,max=100)

            result=self.make_twoDgaussian_fit(axis=axes,data=data,add_parameters=para)

#            print(result.fit_report())
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


        def oneD_testing(self):
            self.x = np.linspace(0, 5, 11)
            x_nice=np.linspace(0, 5, 101)

            mod_final,params = self.make_gaussian_model()
#            print('Parameters of the model',mod_final.param_names)

            p=Parameters()

#            p.add('center',max=+3)

            self.data_noisy=mod_final.eval(x=self.x, amplitude=100000,center=1,sigma=1.2, c=10000) + 8000*abs(np.random.normal(size=self.x.shape))
#            print(self.data_noisy)
            result=self.make_gaussian_fit(axis=self.x,data=self.data_noisy,add_parameters=p)


            gaus=gaussian(3,5)
            self.data_smooth = filters.convolve1d(self.data_noisy, gaus/gaus.sum(),mode='mirror')

            plt.plot(self.x,self.data_noisy)
            plt.plot(self.x,self.data_smooth,'-k')
            plt.plot(self.x,result.init_fit,'-g',label='init')
#            plt.plot(self.x,result.best_fit,'-r',label='fit')
            plt.plot(x_nice,mod_final.eval(x=x_nice,params=result.params),'-r',label='fit')
            plt.show()
            print(result.init_params)
#            print(result.fit_report(show_correl=False))


        def useful_object_variables(self):
            x = np.linspace(2800, 2900, 101)


            ##there are useful builtin models: Constantmodel(), LinearModel(),GaussianModel()
#                LorentzianModel(),DampedOscillatorModel()

            #but you can also define your own:
            model,params = self.make_lorentzian_model()
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

            result=self.make_lorentzian_fit(x,data_noisy,add_parameters=para)

#            print('success',result.success)
#            print('best value',result.best_values['center'])
##
#            print('Fit report:',result.fit_report())

            plt.plot(x,data_noisy)
#            plt.plot(x,result.init_fit,'-g')
#            plt.plot(x,result.best_fit,'-r')
            plt.show()

#            data_smooth,offset=self.find_offset_parameter(x,data_noisy)
#            plt.plot(data_noisy,'-b')
#            plt.plot(data_smooth,'-r')
#            plt.show()


        def double_lorentzian_testing(self):
            for ii in range(1):
#                time.sleep(0.51)
                start=2800
                stop=2950
                num_points=int((stop-start)/2)
                x = np.linspace(start, stop, num_points)

                mod,params = self.make_multiplelorentzian_model(no_of_lor=2)
    #            print('Parameters of the model',mod.param_names)

                p=Parameters()

                #============ Create data ==========

#                center=np.random.random(1)*50+2805
    #            p.add('center',max=-1)
                p.add('lorentz0_amplitude',value=-abs(np.random.random(1)*50+100))
                p.add('lorentz0_center',value=np.random.random(1)*150.0+2800)
                p.add('lorentz0_sigma',value=abs(np.random.random(1)*2.+1.))
                p.add('lorentz1_center',value=np.random.random(1)*150.0+2800)
                p.add('lorentz1_sigma',value=abs(np.random.random(1)*2.+1.))
                p.add('lorentz1_amplitude',value=-abs(np.random.random(1)*50+100))


#                p.add('lorentz0_amplitude',value=-1500)
#                p.add('lorentz0_center',value=2860)
#                p.add('lorentz0_sigma',value=12)
#                p.add('lorentz1_amplitude',value=-1500)
#                p.add('lorentz1_center',value=2900)
#                p.add('lorentz1_sigma',value=12)
                p.add('c',value=100.)

#                print(p)
##               von odmr dummy
#                sigma=7.
#                length=stop-start
#                plt.rcParams['figure.figsize'] = (10.0, 3.0)
#                p.add('lorentz0_amplitude',value=-20000.*np.pi*sigma)
#                p.add('lorentz0_center',value=length/3+start)
#                p.add('lorentz0_sigma',value=sigma)
#                p.add('lorentz1_amplitude',value=-15000*np.pi*sigma)
#                p.add('lorentz1_center',value=2*length/3+start)
#                p.add('lorentz1_sigma',value=sigma)
#                p.add('c',value=80000.)
#                print(p['lorentz0_center'].value,p['lorentz1_center'].value)
#                print('center left, right',p['lorentz0_center'].value,p['lorentz1_center'].value)
                data_noisy=(mod.eval(x=x,params=p)
                                        + 2*np.random.normal(size=x.shape))
#                data_noisy=np.loadtxt('C:\\Data\\2016\\03\\20160321\\ODMR\\20160321-0938-11_ODMR_data.dat')[:,1]
#                x=np.loadtxt('C:\\Data\\2016\\03\\20160321\\ODMR\\20160321-0938-11_ODMR_data.dat')[:,0]
                para=Parameters()
#                para.add('lorentz1_center',value=2*length/3+start)
#                para.add('bounded',expr='abs(lorentz0_center-lorentz1_center)>10')
#                para.add('delta',value=20,min=10)
#                para.add('lorentz1_center',expr='lorentz0_center+delta')
#                print(para['delta'])
#                para.add('lorentz1_center',expr='lorentz0_center+10.0')
#                error, lorentz0_amplitude,lorentz1_amplitude, lorentz0_center,lorentz1_center, lorentz0_sigma,lorentz1_sigma, offset = self.estimate_double_lorentz(x,data_noisy)

#                print(lorentz0_center>lorentz1_center)
                result=self.make_doublelorentzian_fit(axis=x,data=data_noisy,add_parameters=para)
#                print(result)
#                print('center 1 und 2',result.init_values['lorentz0_center'],result.init_values['lorentz1_center'])

#                print('center 1 und 2',result.best_values['lorentz0_center'],result.best_values['lorentz1_center'])
                #           gaussian filter
#                gaus=gaussian(10,10)
#                data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum())

                data_smooth, offset = self.find_offset_parameter(x,data_noisy)

#                print('Offset:',offset)
#                print('Success:',result.success)
#                print(result.message)
#                print(result.lmdif_message)
#                print(result.fit_report(show_correl=False))

                data_level=data_smooth-offset

                #search for double lorentzian

                error, \
                sigma0_argleft, dip0_arg, sigma0_argright, \
                sigma1_argleft, dip1_arg , sigma1_argright = \
                self._search_double_dip(x, data_level,make_prints=False)

                print(x[sigma0_argleft], x[dip0_arg], x[sigma0_argright], x[sigma1_argleft], x[dip1_arg], x[sigma1_argright])
                print(x[dip0_arg], x[dip1_arg])

                plt.plot((x[sigma0_argleft], x[sigma0_argleft]), ( data_noisy.min() ,data_noisy.max()), 'b-')
                plt.plot((x[sigma0_argright], x[sigma0_argright]), (data_noisy.min() ,data_noisy.max()), 'b-')

                plt.plot((x[sigma1_argleft], x[sigma1_argleft]), ( data_noisy.min() ,data_noisy.max()), 'k-')
                plt.plot((x[sigma1_argright], x[sigma1_argright]), ( data_noisy.min() ,data_noisy.max()), 'k-')

                try:
    #            print(result.fit_report()
                    plt.plot(x,data_noisy,'o')
                    plt.plot(x,result.init_fit,'-y')
                    plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
                    plt.plot(x,data_smooth,'-g')
                except:
                    print('exception')
    ##            plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'-r')#
                plt.show()

#                print('Peaks:',p['lorentz0_center'].value,p['lorentz1_center'].value)
#                print('Estimator:',result.init_values['lorentz0_center'],result.init_values['lorentz1_center'])
#
#                data=-1*data_smooth+data_smooth.max()
##                print('peakutils',x[ peakutils.indexes(data, thres=1.1/max(data), min_dist=1)])
#                indices= peakutils.indexes(data, thres=5/max(data), min_dist=2)
#                print('Peakutils',x[indices])
#                pplot(x,data,indices)


#                if p['lorentz0_center'].value<p['lorentz1_center'].value:
#                    results[0,ii]=p['lorentz0_center'].value
#                    results[1,ii]=p['lorentz1_center'].value
#                else:
#                    results[0,ii]=p['lorentz1_center'].value
#                    results[1,ii]=p['lorentz0_center'].value
#                if result.best_values['lorentz0_center']<result.best_values['lorentz1_center']:
#                    results[2,ii]=result.best_values['lorentz0_center']
#                    results[3,ii]=result.best_values['lorentz1_center']
#                else:
#                    results[2,ii]=result.best_values['lorentz1_center']
#                    results[3,ii]=result.best_values['lorentz0_center']
#                time.sleep(1)
#            plt.plot(runs[:],results[0,:],'-r')
#            plt.plot(runs[:],results[1,:],'-g')
#            plt.plot(runs[:],results[2,:],'-b')
#            plt.plot(runs[:],results[3,:],'-y')
#            plt.show()
        def double_lorentzian_fixedsplitting_testing(self):
            # This method does not work and has to be fixed!!!
            for ii in range(1):
#                time.sleep(0.51)
                start=2800
                stop=2950
                num_points=int((stop-start)/2)
                x = np.linspace(start, stop, num_points)

                mod,params = self.make_multiplelorentzian_model(no_of_lor=2)

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

                result=self.make_doublelorentzian_fit(axis=x,data=data_noisy,add_parameters=para)


                data_smooth, offset = self.find_offset_parameter(x,data_noisy)

                data_level=data_smooth-offset

                #search for double lorentzian

                error, \
                sigma0_argleft, dip0_arg, sigma0_argright, \
                sigma1_argleft, dip1_arg , sigma1_argright = \
                self._search_double_dip(x, data_level,make_prints=False)

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

        def lorentzian_testing(self):
            x = np.linspace(800, 1000, 301)

            mod,params = self.make_lorentzian_model()
            print('Parameters of the model',mod.param_names)
            p=Parameters()

            params.add('amplitude',value=-30.)
            params.add('center',value=920.)
            params.add('sigma',value=10)
            params.add('c',value=10.)

            data_noisy=(mod.eval(x=x,params=params)
                                    + 0.2*np.random.normal(size=x.shape))

            para=Parameters()
#            para.add('sigma',value=p['sigma'].value)
#            para.add('amplitude',value=p['amplitude'].value)

#            result=mod.fit(data_noisy,x=x,params=p)
            result=self.make_lorentzian_fit(axis=x,data=data_noisy,add_parameters=para)
#            result=mod.fit(axis=x,data=data_noisy,add_parameters=p)

#            print(result.fit_report())
#           gaussian filter
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum())

            print(result.init_values['c'])
            plt.plot(x,data_noisy)
            plt.plot(x,result.init_fit,'-g')
            plt.plot(x,result.best_fit,'-r')
            plt.plot(x,data_smooth,'-y')

#            plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'-r')
            plt.show()

        def double_gaussian_testing(self):
            for ii in range(1):
#                time.sleep(0.51)
                start=000000
                stop=500000
                num_points=int((stop-start)/2000)
                x = np.linspace(start, stop, num_points)

                mod,params = self.make_multiplegaussian_model(no_of_gauss=2)
    #            print('Parameters of the model',mod.param_names)

                amplitude=75000+np.random.random(1)*50000
                sigma0=25000+np.random.random(1)*20000
                sigma1=25000+np.random.random(1)*20000
                splitting=100000  # abs(np.random.random(1)*300000)

                p=Parameters()
                p.add('gaussian0_amplitude',value=amplitude)
                p.add('gaussian0_center',value=160000)
                p.add('gaussian0_sigma',value=sigma0)
                p.add('gaussian1_amplitude',value=amplitude*1.5)
                p.add('gaussian1_center',value=300000)
                p.add('gaussian1_sigma',value=sigma1)
                p.add('c',value=0.)

                data_noisy=(mod.eval(x=x,params=p)
                                        + 0.0*np.random.normal(size=x.shape))

#                np.savetxt('data',data_noisy)

#                data_noisy=np.loadtxt('data')
#                para=Parameters()
#                result=self.make_doublegaussian_fit(axis=x,data=data_noisy,add_parameters=para)
#
                #make the filter an extra function shared and usable for other functions
                gaus=gaussian(10,10)
                data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')

#                set optimal thresholds
                threshold_fraction=0.4
                minimal_threshold=0.2
                sigma_threshold_fraction=0.3

                error, \
                sigma0_argleft, dip0_arg, sigma0_argright, \
                sigma1_argleft, dip1_arg , sigma1_argright = \
                self._search_double_dip(x, data_smooth*-1,
                                        threshold_fraction=threshold_fraction,
                                        minimal_threshold=minimal_threshold,
                                        sigma_threshold_fraction=sigma_threshold_fraction,
                                        make_prints=False)

                print(x[sigma0_argleft], x[dip0_arg], x[sigma0_argright], x[sigma1_argleft], x[dip1_arg], x[sigma1_argright])
                print(x[dip0_arg], x[dip1_arg])

                plt.plot((x[sigma0_argleft], x[sigma0_argleft]), ( data_noisy.min() ,data_noisy.max()), 'b-')
                plt.plot((x[sigma0_argright], x[sigma0_argright]), (data_noisy.min() ,data_noisy.max()), 'b-')

                plt.plot((x[sigma1_argleft], x[sigma1_argleft]), ( data_noisy.min() ,data_noisy.max()), 'k-')
                plt.plot((x[sigma1_argright], x[sigma1_argright]), ( data_noisy.min() ,data_noisy.max()), 'k-')

                paramdict = dict()
                paramdict['gaussian0_amplitude'] = {'gaussian0_amplitude':amplitude}
                paramdict['gaussian0_center'] = {'gaussian0_center':160000}
                paramdict['gaussian0_sigma'] = {'gaussian0_sigma':sigma0}
                paramdict['gaussian1_amplitude'] = {'gaussian1_amplitude':amplitude*1.5}
                paramdict['gaussian1_center'] = {'gaussian1_center':300000}
                paramdict['gaussian1_sigma'] = {'gaussian1_sigma':sigma1}
                paramdict['c'] = {'c':0}

                result=self.make_doublegaussian_fit(x,data_noisy,add_parameters = paramdict,estimator='gated_counter',
                                        threshold_fraction=threshold_fraction,
                                        minimal_threshold=minimal_threshold,
                                        sigma_threshold_fraction=sigma_threshold_fraction)

                plt.plot((result.init_values['gaussian0_center'], result.init_values['gaussian0_center']), ( data_noisy.min() ,data_noisy.max()), 'r-')
                plt.plot((result.init_values['gaussian1_center'], result.init_values['gaussian1_center']), ( data_noisy.min() ,data_noisy.max()), 'r-')
                print(result.init_values['gaussian0_center'],result.init_values['gaussian1_center'])
#                gaus=gaussian(20,10)
#                data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')
#                data_der=np.gradient(data_smooth)
                print(result.fit_report())
                print(result.message)
                print(result.success)
#                print(result.params)
                print(result.errorbars)

######################################################

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

        def powerfluorescence_testing(self):
            x = np.linspace(1, 1000, 101)
            mod,params = self.make_powerfluorescence_model()
            print('Parameters of the model',mod.param_names,' with the independet variable',mod.independent_vars)

            params['I_saturation'].value=200.
            params['slope'].value=0.25
            params['intercept'].value=2.
            params['P_saturation'].value=100.
            data_noisy=(mod.eval(x=x,params=params)
                                    + 10*np.random.normal(size=x.shape))

            para=Parameters()
            para.add('I_saturation',value=152.)
            para.add('slope',value=0.3,vary=True)
            para.add('intercept',value=0.3,vary=False,min=0.) #dark counts
            para.add('P_saturation',value=130.   )


#            data=np.loadtxt('Po_Fl.txt')

            result=self.make_powerfluorescence_fit(axis=x,data=data_noisy,add_parameters=para)
#            result=self.make_powerfluorescence_fit(axis=data[:,0],data=data[:,2]/1000,add_parameters=para)

            print(result.fit_report())

#            x_nice= np.linspace(0,data[:,0].max(), 101)

#            plt.plot(data[:,0],data[:,2]/1000,'ob')

            plt.plot(x,mod.eval(x=x,params=para),'-g')

            plt.plot(x,mod.eval(x=x,params=result.params),'-r')
            plt.show()

            print(result.message)

        def double_gaussian_odmr_testing(self):
            for ii in range(1):

                start=2800
                stop=2950
                num_points=int((stop-start)/2)
                x = np.linspace(start, stop, num_points)

                mod,params = self.make_multiplelorentzian_model(no_of_lor=2)
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


                data_smooth, offset = self.find_offset_parameter(x,data_noisy)

                data_level=(data_smooth-offset)
#                set optimal thresholds
                threshold_fraction=0.4
                minimal_threshold=0.2
                sigma_threshold_fraction=0.3

                error, \
                sigma0_argleft, dip0_arg, sigma0_argright, \
                sigma1_argleft, dip1_arg , sigma1_argright = \
                self._search_double_dip(x, data_level,
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

                mod, params = self.make_multiplegaussian_model(no_of_gauss=2)

#                params['gaussian0_center'].value=x[dip0_arg]
#                params['gaussian0_center'].min=x.min()
#                params['gaussian0_center'].max=x.max()
#                params['gaussian1_center'].value=x[dip1_arg]
#                params['gaussian1_center'].min=x.min()
#                params['gaussian1_center'].max=x.max()



                result=self.make_doublegaussian_fit(x,data_noisy,
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

        def sine_testing(self):

            x_axis = np.linspace(0, 50, 151)
            x_nice = np.linspace(x_axis[0],x_axis[-1], 1000)
            mod,params = self.make_sine_model()
            print('Parameters of the model',mod.param_names,' with the independet variable',mod.independent_vars)

            print(1/(x_axis[1]-x_axis[0]))
            params['amplitude'].value=0.2 + np.random.normal(0,0.4)
            params['frequency'].value=0.1+np.random.normal(0,0.5)
            params['phase'].value=np.pi*1.0
            params['offset'].value=0.94+np.random.normal(0,0.4)
            data_noisy=(mod.eval(x=x_axis,params=params)
                                    + 0.5*np.random.normal(size=x_axis.shape))


            # set the offset as the average of the data
            offset = np.average(data_noisy)

            # level data
            data_level = data_noisy - offset

            # estimate amplitude
 #           params['amplitude'].value = max(data_level.max(), np.abs(data_level.min()))

            # perform fourier transform
            data_level_zeropaded=np.zeros(int(len(data_level)*2))
            data_level_zeropaded[:len(data_level)]=data_level
            fourier = np.fft.fft(data_level_zeropaded)
            stepsize = x_axis[1]-x_axis[0]  # for frequency axis
            freq = np.fft.fftfreq(data_level_zeropaded.size, stepsize)
            frequency_max = np.abs(freq[np.log(fourier).argmax()])

            print(params['frequency'].value,np.round(frequency_max,3))
#            plt.xlim(0,freq.max())
            plt.plot(freq[:int(len(freq)/2)],abs(fourier)[:int(len(freq)/2)])
#            plt.plot(freq,np.log(abs(fourier)),'-r')
            plt.show()

            print('offset',offset)
#            print((x_axis[-1]-x_axis[0])*frequency_max)

           # shift_tmp = (data_level[0])/params['amplitude'].value
            #shift = abs(np.arcsin(shift_tmp))
#            print('shift', shift)
#            if np.gradient(data_noisy)[0]<0 and data_level[0]>0:
#                shift=np.pi-shift
#                print('ho ', shift)
 #           elif np.gradient(data_noisy)[0]<0 and data_level[0]<0:
  #              shift+=np.pi
   #             print('hi1')
    #        elif np.gradient(data_noisy)[0]>0 and data_level[0]<0:
     #           shift = 2.*np.pi - shift
      #          print('hi2')

       #     print(params['phase'].value,shift)


#            params['frequency'].value = frequency_max
 #           params['phase'].value = shift
  #          params['offset'].value = offset

#            print(params.pretty_print())
#            print(data_noisy)
#            para={}
 #           para['phase'] = {'vary': False, 'value': np.pi/2.}
  #          para['amplitude'] = {'min': 0.0}

            result=self.make_sine_fit(axis=x_axis,data=data_noisy,add_parameters=None)
##            result=self.make_powerfluorescence_fit(axis=data[:,0],data=data[:,2]/1000,add_parameters=para)
#
#            print(result.fit_report())

#            x_nice= np.linspace(0,data[:,0].max(), 101)

#            plt.plot(data[:,0],data[:,2]/1000,'ob')

            plt.plot(x_nice,mod.eval(x=x_nice,params=params),'-g')
            plt.plot(x_axis,data_noisy,'ob')
            plt.plot(x_axis,result.init_fit,'-y')
            plt.plot(x_axis,result.best_fit,'-r',linewidth=2.0,)
            #plt.plot(x_axis,np.gradient(data_noisy)+offset,'-g',linewidth=2.0,)

            plt.show()

#            print(result.fit_report())

#            units=dict()
#            units['frequency']='GHz'
 #           units['phase']='rad'
  #          units['offset']='arb. u.'
#            units['amplitude']='arb. u.'
   #         print(self.create_fit_string(result,mod,units))

    #        print(result.best_values['phase']/np.pi*180)



        def twoD_gaussian_magnet(self):
            gmod,params = self.make_twoDgaussian_model()
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
                gmod,params = self.make_twoDgaussian_model()
                data= gmod.eval(x=axes,amplitude=amplitude,x_zero=x_zero,
                                y_zero=y_zero,sigma_x=sigma_x,sigma_y=sigma_y,
                                theta=theta_here, offset=offset)
                data+=5*np.random.random_sample(np.shape(data))
                xx, yy = np.meshgrid(x, y)
                axes=(xx.flatten(),yy.flatten())

            para=Parameters()
            para.add('theta',value=-0.15/np.pi,vary=True)
#            para.add('x_zero',expr='0.5*y_zero')
#            para.add('sigma_x',value=0.05,vary=True )
#            para.add('sigma_y',value=0.3,vary=True )
            para.add('amplitude',min=0.0, max= 100)
            para.add('offset',min=0.0, max= 3000)
#            para.add('sigma_y',min=0.2*((15.-13.)/12.) , max=   10*(y[-1]-y[0]))
#            para.add('x_zero',value=40,min=50,max=100)

            result=self.make_twoDgaussian_fit(axis=axes,data=data,add_parameters=para)
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


        def double_poissonian_testing(self):
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
            mod_final, params = self.make_poissonian_model(no_of_functions=2)

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

            search_res = self._search_double_dip(x_axis_interpol,
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
            params['poissonian0_mu'].value = x_axis_interpol[dip0_arg]
            params['poissonian0_amplitude'].value = (interpol_hist[dip0_arg] / self.poisson(x_axis_interpol[dip0_arg], x_axis_interpol[dip0_arg]))

            params['poissonian1_mu'].value = x_axis_interpol[dip1_arg]
            params['poissonian1_amplitude'].value = ( interpol_hist[dip1_arg] / self.poisson(x_axis_interpol[dip1_arg], x_axis_interpol[dip1_arg]))

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

        def double_poissonian_testing2(self):
            """ Testing of double poissonian with self created data.
            First version of double poissonian fit."""

            start=100
            stop=300
            num_points=int((stop-start)+1)*100
            x = np.linspace(start, stop, num_points)

            # double poissonian
            mod,params = self.make_poissonian_model(no_of_functions=2)
            print('Parameters of the model',mod.param_names)
            parameter=Parameters()
            parameter.add('poissonian0_mu',value=200)
            parameter.add('poissonian1_mu',value=240)
            parameter.add('poissonian0_amplitude',value=1)
            parameter.add('poissonian1_amplitude',value=1)
            data_noisy = ( np.array(mod.eval(x=x,params=parameter)) *
                           np.array((1+0.2*np.random.normal(size=x.shape) )*
                           parameter['poissonian1_amplitude'].value) )


            #make the filter an extra function shared and usable for other functions
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')

            result = self.make_doublepoissonian_fit(x,data_noisy)
            print(result.fit_report())

            try:
                plt.plot(x, data_noisy, '-b')
                plt.plot(x, data_smooth, '-g')
                plt.plot(x,result.init_fit,'-y')
                plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
                plt.show()


            except:
                print('exception')


        def poissonian_testing(self):
            start=0
            stop=30
            mu=8
            num_points=1000
            x = np.array(np.linspace(start, stop, num_points))
#            x = np.array(x,dtype=np.int64)
            mod,params = self.make_poissonian_model()
            print('Parameters of the model',mod.param_names)

            p=Parameters()
            p.add('poissonian_mu',value=mu)
            p.add('poissonian_amplitude',value=200.)

            data_noisy=(mod.eval(x=x,params=p) *
                        np.array((1+0.001*np.random.normal(size=x.shape) *
                        p['poissonian_amplitude'].value ) ) )

            print('all int',all(isinstance(item, (np.int32,int, np.int64)) for item in x))
            print('int',isinstance(x[1], int),float(x[1]).is_integer())
            print(type(x[1]))
            #make the filter an extra function shared and usable for other functions
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')


            result = self.make_poissonian_fit(x,data_noisy)
            print(result.fit_report())
            try:
                plt.plot(x, data_noisy, '-b')
                plt.plot(x, data_smooth, '-g')
                plt.plot(x,result.init_fit,'-y')
                plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
                plt.show()


            except:
                print('exception')

        def gaussian_testing(self):
            start=0
            stop=300
            mu=100
            num_points=1000
            x = np.array(np.linspace(start, stop, num_points))
#            x = np.array(x,dtype=np.int64)
            mod,params = self.make_poissonian_model()
#            print('Parameters of the model',mod.param_names)

            p=Parameters()
            p.add('poissonian_mu',value=mu)
            p.add('poissonian_amplitude',value=200.)

            data_noisy=(mod.eval(x=x,params=p) *
                        np.array((1+0.00*np.random.normal(size=x.shape) *
                        p['poissonian_amplitude'].value ) ) )

            #make the filter an extra function shared and usable for other functions
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')

            axis=x
            data=data_noisy
            add_parameters=None

            mod_final, params = self.make_gaussian_model()

            error, params = self.estimate_gaussian(axis, data, params)

            # auxiliary variables
            stepsize = abs(axis[1] - axis[0])
            n_steps = len(axis)

            # Define constraints
            params['center'].min = (axis[0]) - n_steps * stepsize
            params['center'].max = (axis[-1]) + n_steps * stepsize
            params['amplitude'].min = 100  # that is already noise from APD
            params['amplitude'].max = data.max() * params['sigma'].value * np.sqrt(2 * np.pi)
            params['sigma'].min = stepsize
            params['sigma'].max = 3 * (axis[-1] - axis[0])
            params['c'].min = 100  # that is already noise from APD
            params['c'].max = data.max() * params['sigma'].value * np.sqrt(2 * np.pi)

            update_dict=dict()

            # integral of data corresponds to sqrt(2) * Amplitude * Sigma
            function = InterpolatedUnivariateSpline(axis, data_smooth, k=1)
            Integral = function.integral(axis[0], axis[-1])
            amp = data_smooth.max()
            sigma = Integral / (amp) / np.sqrt(2 * np.pi)
            amplitude = amp * sigma * np.sqrt(2 * np.pi)

            update_dict['c']={'min':-np.inf,'max':np.inf,'value':0.1}
            update_dict['center']={'min':-np.inf,'max':np.inf,'value':axis[np.argmax(data_noisy)]}
            update_dict['sigma']={'min':-np.inf,'max':np.inf,'value':sigma}
            update_dict['amplitude']={'min':-np.inf,'max':np.inf,'value':amplitude}
            print('params',params['c'])
            print('dict',update_dict['c'])
            params = self._substitute_parameter(parameters=params, update_dict=update_dict)
            print('params',params['c'])

            # overwrite values of additional parameters
#            if add_parameters is not None:
#                params = self._substitute_parameter(parameters=params,
#                                                    update_parameters=add_parameters)
            try:
                result = mod_final.fit(data, x=axis, params=params)
            except:
                self.logMsg('The 1D gaussian fit did not work.',
                            msgType='warning')
                result = mod_final.fit(data, x=axis, params=params)
                print(result.message)

#            print(params['center'])
#            print(params['c'])
#            print(params['sigma'])
            print(len(params))
#
            print(result.init_params)
            try:
                plt.plot(x, data_noisy, '-b')
                plt.plot(x, data_smooth, '-g')
                plt.plot(x,result.init_fit,'-y')
                plt.plot(x,result.best_fit,'-r',linewidth=2.0,)
                plt.show()


            except:
                print('exception')

            units={'center': 'counts/s','sigma': 'counts','amplitude': 'counts/s','c': 'N'}
            print(self.create_fit_string(result,mod_final,units=units))

################################################################################################################################
        def exponentialdecay_testing(self):
            #generation of data for testing
            x_axis = np.linspace(1, 51, 20)
            x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
            mod, params = self.make_exponentialdecay_model()
            print('Parameters of the model', mod.param_names, ' with the independet variable', mod.independent_vars)

            params['amplitude'].value = -100 + abs(np.random.normal(0,200))
            params['lifetime'].value = 1 + abs(np.random.normal(0,20))
            params['offset'].value = 1 + abs(np.random.normal(0, 200))
            print('\n', 'amplitude', params['amplitude'].value, '\n', 'lifetime',
                      params['lifetime'].value,'\n', 'offset', params['offset'].value)

            data_noisy = (mod.eval(x=x_axis, params=params)
                              + 10* np.random.normal(size=x_axis.shape))
            result = self.make_exponentialdecay_fit(axis=x_axis, data=data_noisy, add_parameters=None)
            data = data_noisy
            offset = data[-max(1,int(len(x_axis)/10)):].mean()

            #substraction of offset
            if data[0]<data[-1]:
                data_level = offset - data
            else:
                data_level = data - offset
            for i in range(0, len(x_axis)):
                if data_level[i] <= data_level.std():
                    break
            print(i)
            try:
                data_level_log = np.log(data_level[0:i])
                linear_result = self.make_linear_fit(axis=x_axis[0:i], data=data_level_log, add_parameters=None)
                plt.plot(x_axis[0:i], data_level_log, 'ob')
                plt.plot(x_axis[0:i], linear_result.best_fit,'-r')
                plt.plot(x_axis[0:i], linear_result.init_fit,'-y')
                plt.show()
            except:#
                plt.plot(x_axis, np.log(data_level), 'or')
                plt.show()
                print("linear fitting poorly conditioned")
            plt.plot(x_axis, data_noisy, 'ob')
            plt.plot(x_nice, mod.eval(x=x_nice, params=params), '-g')
            print(result.fit_report())
            plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0)
            plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0)

                # plt.plot(x_axis, np.gradient(data_noisy), '-g', linewidth=2.0, )
            plt.show()
###########################################################################################
        def bareexponentialdecay_testing(self):
            #generation of data for testing
            x_axis = np.linspace(1, 51, 20)
            x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
            mod, params = self.make_bareexponentialdecay_model()
            print('Parameters of the model', mod.param_names, ' with the independet variable', mod.independent_vars)
            params['lifetime'].value = 1 + abs(np.random.normal(0,25))
            print('\n''lifetime',
                      params['lifetime'].value)
            data_noisy = (mod.eval(x=x_axis, params=params)
                              + 0.25 * np.random.normal(size=x_axis.shape))
            data = abs(data_noisy)
            for i in range(0, len(x_axis)):
                if data[i] <= data.std():
                    break
            print(i)
            data_log = np.log(data[0:i])

            plt.plot(x_axis[0:i], data_log, 'ob')
            linear_result = self.make_linear_fit(axis=x_axis[0:i],data= data_log,add_parameters=None)

            plt.plot(x_axis[0:i], linear_result.best_fit,'-r')
            plt.plot(x_axis[0:i], linear_result.init_fit,'-y')
            plt.show()


            result = self.make_bareexponentialdecay_fit(axis=x_axis, data=data_noisy, add_parameters=None)
            plt.plot(x_axis, data_noisy, 'ob')
            plt.plot(x_nice, mod.eval(x=x_nice, params=params), '-g')
            print(result.fit_report())
            plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0)
            plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0)

                # plt.plot(x_axis, np.gradient(data_noisy), '-g', linewidth=2.0, )
            plt.show()
#############################################################################################
        def sineexponentialdecay_testing(self):
            # generation of data for testing
            x_axis = np.linspace(0, 100, 100)
            x_nice = np.linspace(x_axis[0], x_axis[-1], 1000)
            mod, params = self.make_sineexponentialdecay_model()
            print('Parameters of the model', mod.param_names, ' with the independet variable', mod.independent_vars)

            params['amplitude'].value = abs(1 + abs(np.random.normal(0,4)))
            params['frequency'].value = abs(0.01 + abs(np.random.normal(0,0.2)))
            params['phase'].value = abs(np.random.normal(0,2*np.pi))
            params['offset'].value = 12 + np.random.normal(0,5)
            params['lifetime'].value = abs(0 + abs(np.random.normal(0,70)))
            print('\n', 'amplitude',params['amplitude'].value, '\n', 'frequency',params['frequency'].value,'\n','phase',params['phase'].value, '\n','offset',params['offset'].value, '\n','lifetime', params['lifetime'].value)
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





            result = self.make_sineexponentialdecay_fit(axis=x_axis, data=data_noisy, add_parameters=None)
            plt.plot(x_axis, data_noisy, 'ob')
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
            print(self.create_fit_string(result, mod, units))

##################################################################################################################
        def stretchedexponentialdecay_testing(self):
            x_axis = np.linspace(0, 51, 100)
            x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
            mod, params = self.make_stretchedexponentialdecay_model()
            print('Parameters of the model', mod.param_names, ' with the independet variable', mod.independent_vars)

            params['beta'].value = 2 + abs(np.random.normal(0,0.5))
            params['amplitude'].value = 10 #- abs(np.random.normal(0,20))
            params['lifetime'].value =1 + abs(np.random.normal(0,30))
            params['offset'].value = 1 + abs(np.random.normal(0, 20))
            print('\n', 'amplitude', params['amplitude'].value, '\n', 'lifetime',
                      params['lifetime'].value,'\n', 'offset',
                         params['offset'].value,'\n', 'beta',
                             params['beta'].value)
            data_noisy = (mod.eval(x=x_axis, params=params)
                          + 1.5* np.random.normal(size=x_axis.shape))

            result = self.make_stretchedexponentialdecay_fit(axis=x_axis,
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
                linear_result = self.make_linear_fit(axis=X, data=double_lg_data,
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

##################################################################################################################
        def linear_testing(self):
            x_axis = np.linspace(1, 51, 100)
            x_nice = np.linspace(x_axis[0], x_axis[-1], 100)
            mod, params = self.make_linear_model()
            print('Parameters of the model', mod.param_names, ' with the independet variable', mod.independent_vars)

            params['slope'].value = 2  # + abs(np.random.normal(0,1))
            params['offset'].value = 50 #+ abs(np.random.normal(0, 200))
            #print('\n', 'beta', params['beta'].value, '\n', 'lifetime',
                  #params['lifetime'].value)
            data_noisy = (mod.eval(x=x_axis, params=params)
                          + 10 * np.random.normal(size=x_axis.shape))

            result = self.make_linear_fit(axis=x_axis, data=data_noisy, add_parameters=None)
            plt.plot(x_axis, data_noisy, 'ob')
            plt.plot(x_nice, mod.eval(x=x_nice, params=params), '-g')
            print(result.fit_report())
            plt.plot(x_axis, result.best_fit, '-r', linewidth=2.0)
            plt.plot(x_axis, result.init_fit, '-y', linewidth=2.0)

            plt.show()


plt.rcParams['figure.figsize'] = (10,5)

test=FitLogic()
#test.N14_testing()
#test.N14_testing2()
#test.N15_testing()
#test.oneD_testing()
#test.gaussian_testing()
#test.twoD_testing()
#test.lorentzian_testing()
#test.double_gaussian_testing()
#test.double_gaussian_odmr_testing()
#test.double_lorentzian_testing()
#test.double_lorentzian_fixedsplitting_testing()
#test.powerfluorescence_testing()
#test.sine_testing()
#test.twoD_gaussian_magnet()
#test.poissonian_testing()
test.double_poissonian_testing()
# test.bareexponentialdecay_testing()
#test.exponentialdecay_testing()
#test.sineexponentialdecay_testing()
#test.stretchedexponentialdecay_testing()
#test.linear_testing()

