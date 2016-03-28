# -*- coding: utf-8 -*-

import numpy as np
import scipy.optimize as opt
from scipy.interpolate import InterpolatedUnivariateSpline
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel,LinearModel
from lmfit import Parameters
import scipy
import matplotlib.pylab as plt

#for filters:
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import time
import random

#import peakutils
#from peakutils.plot import plot as pplot

"""
General procedure to create new fitting routines:

A fitting routine consists out of three major parts:
    1. a (mathematical) Model you have for the passed data
            * Here we use the lmfit package, which has a couple of standard
              models like ConstantModel, LorentzianModel or GaussianModel.
              These models can be used straight away and also can be added, like:
              new_model = ConstantModel()+GaussianModel(), which yields a
              Gaussian model with an offset.
            * If there is no standard model one can define a customized model,
              see make_sine_model()
            * With model.make_params() one can create a set of parameters with
              a value, min, max, vary and an expression. These parameters are
              returned as a Parameters object which contains all variables
              in a dictionary.
            * The make_"..."_model method returns, the model and parameter
              dictionary
    2. an Estimator, which can extract from the passed data initial values for
       the fitting routine.
            * Here values have to be estimated from the raw data
            * In many cases a clever convolution helps a lot
            * Offsets can be retrieved from find_offset_parameter method
            * All parameters are given via a Parameters object
            * The estimated values are returned by a Parameters object
    3. The actual fit method
            * First the model and parameters are created with the make_model
              method.
            * The initial values are returned by the estimator method
            * Constraints are set, e.g. param['offset'].min=0
                                        param['offset'].max=data.max()
            * Additional parameters given by inputs can be overwritten by
              _substitute_parameter method
            * Finally fit is done via model.fit(data, x=axis,params=params)
            * The fit routine from lmfit returns a dictionary with many
              parameters like: results with errors and correlations,
              best_values, initial_values, success flag,
              an error message.
            * With model.eval(...) one can generate high resolution data by
              setting an x-axis with maby points

The power of that general splitting is that you can write pretty independent
fit algorithms, but their efficiency will (very often) rely on the quality of
the estimator.
"""


class FitLogic():
        """
        UNSTABLE:Jochen Scheuer
        This is the fitting class where fit models are defined and methods
        are implemented to process the data.
        
        """
    
    
    ############################################################################
    #                                                                          #
    #                             General methods                              #
    #                                                                          #
    ############################################################################

        def _substitute_parameter(self, parameters=None, update_parameters=None):
            """ This method substitutes all parameters handed in the
            update_parameters object in an initial set of parameters.

            @param object parameters: lmfit.parameter.Parameters object, initial
                                      parameters
            @param object update_parameters: lmfit.parameter.Parameters object, new
                                             parameters

            @return object parameters: lmfit.parameter.Parameters object, new object
                                       with substituted parameters
            """

            for para in update_parameters:

                #first check if completely new parameter, which is added in the else
                if para in parameters:
                    #store value because when max,min is set the value is overwritten
                    store_value = parameters[para].value

                    # the Parameter object changes the value, min and max when the
                    # value is called therefore the parameters have to be saved from
                    # the reseted Parameter object therefore the Parameters have to be
                    # saved also here

                    para_temp = update_parameters
                    if para_temp[para].value is not None:
                        value_new = True
                        value_value = para_temp[para].value
                    else:
                        value_new = False

                    para_temp = update_parameters
                    if para_temp[para].min is not None:
                        min_new = True
                        min_value = para_temp[para].min
                    else:
                        min_new = False

                    para_temp = update_parameters
                    if para_temp[para].max is not None:
                        max_new = True
                        max_value = para_temp[para].max
                    else:
                        max_new = False

                    # vary is set by default to True
                    parameters[para].vary = update_parameters[para].vary

                    # if the min, max and expression and value are new overwrite
                    # them here

                    if min_new:
                        parameters[para].min = update_parameters[para].min

                    if max_new:
                        parameters[para].max = update_parameters[para].max

                    if update_parameters[para].expr is not None:
                        parameters[para].expr = update_parameters[para].expr

                    if value_new:
                        parameters[para].value = value_value

                    # if the min or max are changed they overwrite the value
                    # therefore here the values have to be reseted to the initial
                    # value also when no new value was set in the beginning

                    if min_new:
                        # in case the value is 0, devision by 0 has to be avoided
                        if parameters[para].value < 1e-12:
                            if abs((min_value+1.)/(parameters[para].value+1.)-1.) < 1e-12:
                                parameters[para].value = store_value
                        else:
                            if abs(min_value/parameters[para].value-1.)<1e-12:
                                parameters[para].value = store_value
                    if max_new:
                        # in case the value is 0, devision by 0 has to be avoided
                        if parameters[para].value < 1e-12:
                            if abs((max_value+1.)/(parameters[para].value+1.)-1.) < 1e-12:
                                parameters[para].value=store_value
                        else:
                            if abs(max_value/parameters[para].value-1.) < 1e-12:
                                parameters[para].value=store_value

                    # check if the suggested value or the value in parameters is
                    # smaller/bigger than min/max values and set then the value to
                    # min or max

                    if min_new:
                        if parameters[para].value<min_value:
                            parameters[para].value=min_value

                    if max_new:
                        if parameters[para].value>max_value:
                            parameters[para].value=max_value
                else:
                    #if parameter is new add here
                    parameters.add(para)

            return parameters

    ############################################################################
    #                                                                          #
    #                          1D gaussian model                               #
    #                                                                          #
    ############################################################################

        def make_gaussian_model(self):
            """ This method creates a model of a gaussian with an offset.

            @return tuple: (object model, object params)

            Explanation of the objects:
                object lmfit.model.CompositeModel model:
                    A model the lmfit module will use for that fit. Here a
                    gaussian model. Returns an object of the class
                    lmfit.model.CompositeModel.

                object lmfit.parameter.Parameters params:
                    It is basically an OrderedDict, so a dictionary, with keys
                    denoting the parameters as string names and values which are
                    lmfit.parameter.Parameter (without s) objects, keeping the
                    information about the current value.
                    The used model has the Parameter with the meaning:
                        'amplitude' : amplitude
                        'center'    : center
                        'sigm'      : sigma
                        'fwhm'      : full width half maximum
                        'c'         : offset

            For further information have a look in:
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
            """

            model = GaussianModel() + ConstantModel()
            params = model.make_params()

            return model, params

        def make_gaussian_fit(self, axis=None, data=None, add_parameters=None):
            """ This method performes a 1D gaussian fit on the provided data.

            @param array[] axis: axis values
            @param array[]  x_data: data
            @param dict add_parameters: Additional parameters

            @return object result: lmfit.model.ModelFit object, all parameters
                                   provided about the fitting, like: success,
                                   initial fitting values, best fitting values, data
                                   with best fit with given axis,...
            """

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

            # overwrite values of additional parameters
            if add_parameters is not None:
                params = self._substitute_parameter(parameters=params,
                                                    update_parameters=add_parameters)
            try:
                result = mod_final.fit(data, x=axis, params=params)
            except:
                self.logMsg('The 1D gaussian fit did not work.',
                            msgType='message')
                result = mod_final.fit(data, x=axis, params=params)
                print(result.message)

            return result

        def estimate_gaussian(self, x_axis=None, data=None, params=None):
            """ This method provides a one dimensional gaussian function.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to x values
            @param Parameters object params: object includes parameter dictionary which can be set

            @return tuple (error, params):

            Explanation of the return parameter:
                int error: error code (0:OK, -1:error)
                Parameters object params: set parameters of initial values
            """

            error = 0
            # check if parameters make sense
            parameters = [x_axis, data]
            for var in parameters:
                if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.',
                                msgType='error')
                    error = -1
                elif len(np.shape(var)) != 1:
                    self.logMsg('Given parameter is no one dimensional array.',
                                msgType='error')
                    error = -1
            if not isinstance(params, Parameters):
                self.logMsg('Parameters object is not valid in estimate_gaussian.',
                            msgType='error')
                error = -1

            # If the estimator is not good enough one can start improvement with
            # a convolution

            # set parameters
            params['center'].value = x_axis[np.argmax(data)]
            params['sigma'].value = (x_axis.max() - x_axis.min()) / 3.
            params['amplitude'].value = (data.max() - data.min()) * (params['sigma'].value * np.sqrt(2 * np.pi))
            params['c'].value = data.min()

            return error, params

        ############################################################################
        #                                                                          #
        #                            2D gaussian model                             #
        #                                                                          #
        ############################################################################


        def make_twoD_gaussian_fit(self, axis=None, data=None,
                                   add_parameters=None):
            """ This method performes a 2D gaussian fit on the provided data.

            @param array[] axis: axis values
            @param array[]  x_data: data
            @param dict add_parameters: Additional parameters

            @return object result: lmfit.model.ModelFit object, all parameters
                                   provided about the fitting, like: success,
                                   initial fitting values, best fitting values, data
                                   with best fit with given axis,...
            """

            x_axis, y_axis = axis

            error,      \
            amplitude,  \
            x_zero,     \
            y_zero,     \
            sigma_x,    \
            sigma_y,    \
            theta,      \
            offset = self.twoD_gaussian_estimator(x_axis=x_axis,
                                                  y_axis=y_axis, data=data)
            mod, params = self.make_twoD_gaussian_model()

            #auxiliary variables
            stepsize_x=x_axis[1]-x_axis[0]
            stepsize_y=y_axis[1]-y_axis[0]
            n_steps_x=len(x_axis)
            n_steps_y=len(y_axis)

            #When I was sitting in the train coding and my girlfiend was sitting next to me she said: "Look it looks like an animal!" - is it a fox or a rabbit???

            #Defining standard parameters
            #                  (Name,       Value,      Vary,           Min,                             Max,                       Expr)
            params.add_many(('amplitude',   amplitude,  True,        100,                               1e7,                           None),
                           (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(x_axis[-1]-x_axis[0]),          None),
                           (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(y_axis[-1]-y_axis[0]) ,   None),
                           (  'x_zero',    x_zero,      True,     (x_axis[0])-n_steps_x*stepsize_x ,         x_axis[-1]+n_steps_x*stepsize_x,               None),
                           (  'y_zero',     y_zero,     True,    (y_axis[0])-n_steps_y*stepsize_y ,         (y_axis[-1])+n_steps_y*stepsize_y,         None),
                           (  'theta',       0.,        True,           0. ,                             np.pi,               None),
                           (  'offset',      offset,    True,           0,                              1e7,                       None))


    #           redefine values of additional parameters
            if add_parameters is not None:
                params=self._substitute_parameter(parameters=params,
                                                 update_parameters=add_parameters)

            try:
                result=mod.fit(data, x=axis,params=params)
            except:
                result=mod.fit(data, x=axis,params=params)
                self.logMsg('The 2D gaussian fit did not '
                            'work:'+result.message, msgType='message')

            return result

        @staticmethod
        def twoD_gaussian_model(x, amplitude, x_zero, y_zero, sigma_x, sigma_y,
                                theta, offset):

            #FIXME: x_data_tuple: dimension of arrays

            """ This method provides a two dimensional gaussian function.

            @param array[k][M] x_data_tuple: array which is (k,M)-shaped, x and y
                                             values
            @param float or int amplitude: Amplitude of gaussian
            @param float or int x_zero: x value of maximum
            @param float or int y_zero: y value of maximum
            @param float or int sigma_x: standard deviation in x direction
            @param float or int sigma_y: standard deviation in y direction
            @param float or int theta: angle for eliptical gaussians
            @param float or int offset: offset

            @return callable function: returns the function
            """

            # # check if parameters make sense
            # #FIXME: Check for 2D matrix
            # if not isinstance( x,(frozenset, list, set, tuple,\
            #                     np.ndarray)):
            #     self.logMsg('Given range of axes is no array type.',
            #                 msgType='error')
            #
            # parameters=[amplitude,x_zero,y_zero,sigma_x,sigma_y,theta,offset]
            # for var in parameters:
            #     if not isinstance(var,(float,int)):
            #         self.logMsg('Given range of parameter is no float or int.',
            #                     msgType='error')

            (u,v) = x
            x_zero = float(x_zero)
            y_zero = float(y_zero)

            a = (np.cos(theta)**2)/(2*sigma_x**2) \
                                        + (np.sin(theta)**2)/(2*sigma_y**2)
            b = -(np.sin(2*theta))/(4*sigma_x**2) \
                                        + (np.sin(2*theta))/(4*sigma_y**2)
            c = (np.sin(theta)**2)/(2*sigma_x**2) \
                                        + (np.cos(theta)**2)/(2*sigma_y**2)
            g = offset + amplitude*np.exp( - (a*((u-x_zero)**2) \
                                    + 2*b*(u-x_zero)*(v-y_zero) \
                                    + c*((v-y_zero)**2)))
            return g.ravel()

        def make_twoD_gaussian_model(self):
            """ This method creates a model of the 2D gaussian function.

            The parameters are: 'amplitude', 'center', 'sigm, 'fwhm' and offset
            'c'. For function see:

            @return lmfit.model.CompositeModel model: Returns an object of the
                                                      class CompositeModel
            @return lmfit.parameter.Parameters params: Returns an object of the
                                                       class Parameters with all
                                                       parameters for the
                                                       gaussian model.

            """

            model=Model(self.twoD_gaussian_model)
            params=model.make_params()

            return model,params

        def twoD_gaussian_estimator(self, x_axis=None, y_axis=None, data=None):
    #            TODO:Make clever estimator
            #FIXME: 1D array x_axis, y_axis, 2D data???
            """ This method provides a two dimensional gaussian function.

            @param array x_axis: x values
            @param array y_axis: y values
            @param array data: value of each data point corresponding to
                                x and y values

            @return float amplitude: estimated amplitude
            @return float x_zero: estimated x value of maximum
            @return float y_zero: estimated y value of maximum
            @return float sigma_x: estimated standard deviation in x direction
            @return float sigma_y: estimated  standard deviation in y direction
            @return float theta: estimated angle for eliptical gaussians
            @return float offset: estimated offset
            @return int error: error code (0:OK, -1:error)
            """

    #            #needed me 1 hour to think about, but not needed in the end...maybe needed at a later point
    #            len_x=np.where(x_axis[0]==x_axis)[0][1]
    #            len_y=len(data)/len_x


            amplitude=float(data.max()-data.min())

            x_zero = x_axis[data.argmax()]
            y_zero = y_axis[data.argmax()]

            sigma_x=(x_axis.max()-x_axis.min())/3.
            sigma_y =(y_axis.max()-y_axis.min())/3.
            theta=0.0
            offset=float(data.min())
            error=0
            #check for sensible values
            parameters=[x_axis,y_axis,data]
            for var in parameters:
                #FIXME: Why don't you check earlier?
                #FIXME: Check for 1D array, 2D
                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is not an array.', \
                                msgType='error')
                    amplitude=0.
                    x_zero=0.
                    y_zero=0.
                    sigma_x=0.
                    sigma_y =0.
                    theta=0.0
                    offset=0.
                    error=-1

            return error,amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset

        ############################################################################
        #                                                                          #
        #                          Double Gaussian Model                           #
        #                                                                          #
        ############################################################################

        def make_multiple_gaussian_model(self, no_of_gauss=None):
            """ This method creates a model of multiple gaussians with an offset. The
            parameters are: 'amplitude', 'center', 'sigma', 'fwhm' and offset
            'c'. For function see:
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel

            @return lmfit.model.CompositeModel model: Returns an object of the
                                                      class CompositeModel
            @return lmfit.parameter.Parameters params: Returns an object of the
                                                       class Parameters with all
                                                       parameters for the
                                                       lorentzian model.
            """

            model=ConstantModel()
            for ii in range(no_of_gauss):
                model+=GaussianModel(prefix='gaussian{}_'.format(ii))

            params=model.make_params()

            return model, params

        def estimate_double_gaussian(self, x_axis = None, data = None, params = None,
                                     threshold_fraction = 0.4,
                                     minimal_threshold = 0.1,
                                     sigma_threshold_fraction = 0.2):
            """ This method provides a gaussian function.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values
            @param Parameters object params: Needed parameters
            @param float threshold : Threshold to find second gaussian
            @param float minimal_threshold: Threshold is lowerd to minimal this
                                            value as a fraction
            @param float sigma_threshold_fraction: Threshold for detecting
                                                   the end of the peak

            @return int error: error code (0:OK, -1:error)
            @return Parameters object params: estimated values
            """

            error = 0

            #make the filter an extra function shared and usable for other functions
            if len(x_axis)<20.:
                len_x=5
            elif len(x_axis)>=100.:
                len_x=10
            else:
                len_x=int(len(x_axis)/10.)+1

            gaus=gaussian(len_x,len_x)
            data_smooth = filters.convolve1d(data, gaus/gaus.sum(),mode='mirror')

            #search for double gaussian

            error, \
            sigma0_argleft, dip0_arg, sigma0_argright, \
            sigma1_argleft, dip1_arg , sigma1_argright = \
            self._search_double_dip(x_axis, data_smooth*(-1),threshold_fraction, minimal_threshold, sigma_threshold_fraction,make_prints=False)

            #set offset to zero
            params['c'].value = 0.0

            params['gaussian0_center'].value = x_axis[dip0_arg]

            #integral of data corresponds to sqrt(2) * Amplitude * Sigma
            function = InterpolatedUnivariateSpline(x_axis, data_smooth, k=1)
            Integral = function.integral(x_axis[0], x_axis[-1])

            amp_0 = data_smooth[dip0_arg]-params['c'].value
            amp_1 = data_smooth[dip1_arg]-params['c'].value

            params['gaussian0_sigma'].value  = Integral / (amp_0+amp_1)  / np.sqrt(2*np.pi)
            params['gaussian0_amplitude'].value = amp_0*params['gaussian0_sigma'].value*np.sqrt(2*np.pi)

            params['gaussian1_center'].value = x_axis[dip1_arg]
            params['gaussian1_sigma'].value  = Integral / (amp_0+amp_1)  / np.sqrt(2*np.pi)
            params['gaussian1_amplitude'].value = amp_1*params['gaussian1_sigma'].value*np.sqrt(2*np.pi)

            return error, params



        def make_double_gaussian_fit(self, axis = None, data = None,
                                        add_parameters = None,
                                        threshold_fraction = 0.4,
                                        minimal_threshold = 0.2,
                                        sigma_threshold_fraction = 0.3):
            """ This method performes a 1D double gaussian fit on the provided data.

            @param array [] axis: axis values
            @param array[]  x_data: data
            @param dictionary add_parameters: Additional parameters
            @param float threshold : Threshold to find second gaussian
            @param float minimal_threshold: Threshold is lowerd to minimal this
                                            value as a fraction
            @param float sigma_threshold_fraction: Threshold for detecting
                                                   the end of the peak

            @return lmfit.model.ModelFit result: All parameters provided about
                                                 the fitting, like: success,
                                                 initial fitting values, best
                                                 fitting values, data with best
                                                 fit with given axis,...

            """

            model, params = self.make_multiple_gaussian_model(no_of_gauss=2)

            error, params = self.estimate_double_gaussian(axis, data, params,
                                                          threshold_fraction,
                                                          minimal_threshold,
                                                          sigma_threshold_fraction)

            #Defining constraints
            params['c'].min=0.0

            params['gaussian0_amplitude'].min=0.0
            params['gaussian1_amplitude'].min=0.0


            #redefine values of additional parameters
            if add_parameters is not None:
                params=self._substitute_parameter(parameters=params,
                                                 update_parameters=add_parameters)
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                result=model.fit(data, x=axis,params=params)
                self.logMsg('The double gaussian fit did not '
                            'work:'+result.message,
                            msgType='message')

            return result



        ############################################################################
        #                                                                          #
        #             Additional routines for Lorentzian-like models               #
        #                                                                          #
        ############################################################################

        def find_offset_parameter(self, x_values=None, data=None):
            """ This method convolves the data with a Lorentzian and the finds the
            offset which is supposed to be the most likely valy via a histogram.
            Additional the smoothed data is returned

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values

            @return int error: error code (0:OK, -1:error)
            @return float array data_smooth: smoothed data
            @return float offset: estimated offset


            """
            #lorentzian filter
            mod,params = self.make_lorentzian_model()

            if len(x_values)<20.:
                len_x=5
            elif len(x_values)>=100.:
                len_x=10
            else:
                len_x=int(len(x_values)/10.)+1

            lorentz=mod.eval(x=np.linspace(0,len_x,len_x), amplitude=1, c=0.,
                             sigma=len_x/4., center=len_x/2.)
            data_smooth = filters.convolve1d(data, lorentz/lorentz.sum(),
                                             mode='constant', cval=data.max())

            #finding most frequent value which is supposed to be the offset
            hist=np.histogram(data_smooth,bins=10)
            offset=(hist[1][hist[0].argmax()]+hist[1][hist[0].argmax()+1])/2.

            return data_smooth,offset

        ############################################################################
        #                                                                          #
        #                             Lorentzian Model                             #
        #                                                                          #
        ############################################################################


        def make_lorentzian_model(self):
            """ This method creates a model of lorentzian with an offset. The
            parameters are: 'amplitude', 'center', 'sigma, 'fwhm' and offset
            'c'. For function see:
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel

            @return lmfit.model.CompositeModel model: Returns an object of the
                                                      class CompositeModel
            @return object params: lmfit.parameter.Parameters object, returns an
                                   object of the class Parameters with all
                                   parameters for the lorentzian model.
            """

            model=LorentzianModel()+ConstantModel()
            params=model.make_params()

            return model,params

        def estimate_lorentz(self,x_axis=None,data=None):
            """ This method provides a lorentzian function.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values

            @return int error: error code (0:OK, -1:error)
            @return float amplitude: estimated amplitude
            @return float x_zero: estimated x value of maximum
            @return float sigma_x: estimated standard deviation in x direction
            @return float offset: estimated offset
            """
    #           TODO: make sigma and amplitude good, this is only a dirty fast solution
            error=0
            # check if parameters make sense
            parameters=[x_axis,data]
            for var in parameters:
                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.', msgType='error')
                    error=-1
                elif len(np.shape(var))!=1:
                    self.logMsg('Given parameter is no one dimensional array.',
                                msgType='error')
            #set paraameters

            data_smooth,offset=self.find_offset_parameter(x_axis,data)

            data_level=data-offset
            data_min=data_level.min()
            data_max=data_level.max()

            #estimate sigma
            numerical_integral=np.sum(data_level) * \
                               (abs(x_axis[-1] - x_axis[0])) / len(x_axis)

            if data_max>abs(data_min):
                try:
                    self.logMsg('The lorentzian estimator set the peak to the '
                                'minimal value, if you want to fit a peak instead '
                                'of a dip rewrite the estimator.',
                                msgType='warning')
                except:
                    self.logMsg('The lorentzian estimator set the peak to the '
                                'minimal value, if you want to fit a peak instead '
                                'of a dip rewrite the estimator.',
                                msgType='warning')

            amplitude_median=data_min
            x_zero=x_axis[np.argmin(data_smooth)]

            sigma = numerical_integral / (np.pi * amplitude_median)
            amplitude=amplitude_median * np.pi * sigma

            return error, amplitude, x_zero, sigma, offset

        def make_lorentzian_fit(self, axis=None, data=None,
                                add_parameters=None):
            """ This method performes a 1D lorentzian fit on the provided data.

            @param array [] axis: axis values
            @param array[]  x_data: data
            @param dictionary add_parameters: Additional parameters

            @return object model: lmfit.model.ModelFit object, all parameters
                                  provided about the fitting, like: success,
                                  initial fitting values, best fitting values, data
                                  with best fit with given axis,...
            """

            error,amplitude, x_zero, sigma, offset = self.estimate_lorentz(
                                                                    axis,data)

            model,params = self.make_lorentzian_model()

            #auxiliary variables
            stepsize=axis[1]-axis[0]
            n_steps=len(axis)

            # TODO: Make sigma amplitude and x_zero better
            # Defining standard parameters

            if axis[1]-axis[0]>0:
                #                (Name,       Value,    Vary,  Min,                        Max,                         Expr)
                params.add_many(('amplitude', amplitude, True, None,                       -1e-12,                      None),
                                ('sigma',     sigma,     True, (axis[1]-axis[0])/2 ,       (axis[-1]-axis[0])*10,       None),
                                ('center',    x_zero,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None),
                                ('c',         offset,    True, None,                       None,                        None))


            if axis[0]-axis[1]>0:

            #                   (Name,        Value,  Vary,    Min,                 Max,                  Expr)
                params.add_many(('amplitude', amplitude, True, None,                -1e-12,               None),
                                ('sigma',     sigma,     True, (axis[0]-axis[1])/2, (axis[0]-axis[1])*10, None),
                                ('center',    x_zero,    True, (axis[-1]),          (axis[0]),            None),
                                ('c',         offset,    True, None,                None,                 None))

        #TODO: Add logmessage when value is changed
            #redefine values of additional parameters
            if add_parameters is not None :
                params=self._substitute_parameter(parameters=params,
                                                 update_parameters=add_parameters)
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                result=model.fit(data, x=axis,params=params)
                self.logMsg('The 1D lorentzian fit did not work. Error '
                            'message:'+result.message,
                            msgType='message')
            return result

        ############################################################################
        #                                                                          #
        #                   Lorentz fit for peak instead of dip                    #
        #                                                                          #
        ############################################################################

        def estimate_lorentz_peak (self, x_axis=None, data=None):
            """ This method provides a lorentzian function to fit a peak.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to x values


            @return int error: error code (0:OK, -1:error)
            @return float amplitude: estimated amplitude
            @return float x_zero: estimated x value of maximum
            @return float sigma_x: estimated standard deviation in x direction
            @return float offset: estimated offset
            """

    #           TODO: make sigma and amplitude good, this is only a dirty fast solution
            error=0
            # check if parameters make sense

            parameters=[x_axis,data]
            for var in parameters:
                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.',
                                msgType='error')
                    error=-1
                elif len(np.shape(var))!=1:
                    self.logMsg('Given parameter is no one dimensional array.',
                                msgType='error')
            #set paraameters
            #print('data',data)
            data_smooth,offset=self.find_offset_parameter(x_axis,data)
            #print('offset',offset)
            data_level=data-offset
            data_min=data_level.min()
            data_max=data_level.max()
            #print('data_min',data_min)
            #print('data_max',data_max)
            #estimate sigma

            numerical_integral=np.sum(data_level) * \
                               (np.abs(x_axis[0] - x_axis[-1])) / len(x_axis)



            if data_max<abs(data_min):
                try:
                    self.logMsg('This lorentzian estimator set the peak to the '
                                'maximum value, if you want to fit a dip '
                                'instead of a peak use estimate_lorentz.',
                                msgType='warning')
                except:
                    print('This lorentzian estimator set the peak to the '
                          'maximum value, if you want to fit a dip instead of '
                          'a peak use estimate_lorentz.')

            amplitude_median=data_max
            #x_zero=x_axis[np.argmax(data_smooth)]
            x_zero=x_axis[np.argmax(data)]
            sigma = np.abs(numerical_integral / (np.pi * amplitude_median))
            amplitude=amplitude_median * np.pi * sigma

            #print('amplitude',amplitude)
            #print('x_zero',x_zero)
            #print('offset',offset)

            return error, amplitude, x_zero, sigma, offset

        def make_lorentzian_peak_fit(self, axis=None, data=None,
                                     add_parameters=None):
            """ Perform a 1D Lorentzian peak fit on the provided data.

            @param array [] axis: axis values
            @param array[]  x_data: data
            @param dictionary add_parameters: Additional parameters

            @return lmfit.model.ModelFit result: All parameters provided about
                                                 the fitting, like: success,
                                                 initial fitting values, best
                                                 fitting values, data with best
                                                 fit with given axis,...
            """

            error,      \
            amplitude,  \
            x_zero,     \
            sigma,      \
            offset      = self.estimate_lorentz_peak(axis, data)


            model, params = self.make_lorentzian_model()

            # auxiliary variables:
            stepsize=np.abs(axis[1]-axis[0])
            n_steps=len(axis)

    #            TODO: Make sigma amplitude and x_zero better

            #Defining standard parameters

            if axis[1]-axis[0]>0:

            #                   (Name,        Value,     Vary, Min,                        Max,                         Expr)
                params.add_many(('amplitude', amplitude, True, 2e-12,                      None,                        None),
                                ('sigma',     sigma,     True, (axis[1]-axis[0])/2,        (axis[-1]-axis[0])*10,       None),
                                ('center',    x_zero,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None),
                                ('c',         offset,    True, None,                       None,                        None))
            if axis[0]-axis[1]>0:

            #                   (Name,        Value,     Vary, Min,                  Max,                  Expr)
                params.add_many(('amplitude', amplitude, True, 2e-12,                None,                 None),
                                ('sigma',     sigma,     True, (axis[0]-axis[1])/2 , (axis[0]-axis[1])*10, None),
                                ('center',    x_zero,    True, (axis[-1]),           (axis[0]),            None),
                                ('c',         offset,    True, None,                 None,                 None))

            #TODO: Add logmessage when value is changed
            #redefine values of additional parameters

            if add_parameters is not None :
                params=self._substitute_parameter(parameters=params,
                                                 update_parameters=add_parameters)
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                result=model.fit(data, x=axis,params=params)
                self.logMsg('The 1D gaussian fit did not work. Error '
                            'message:' + result.message,
                            msgType='message')

            return result


        ############################################################################
        #                                                                          #
        #                          Double Lorentzian Model                         #
        #                                                                          #
        ############################################################################

        def make_multiple_lorentzian_model(self, no_of_lor=None):
            """ This method creates a model of lorentzian with an offset. The
            parameters are: 'amplitude', 'center', 'sigm, 'fwhm' and offset
            'c'. For function see:
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel

            @return lmfit.model.CompositeModel model: Returns an object of the
                                                      class CompositeModel
            @return lmfit.parameter.Parameters params: Returns an object of the
                                                       class Parameters with all
                                                       parameters for the
                                                       lorentzian model.
            """

            model=ConstantModel()
            for ii in range(no_of_lor):
                model+=LorentzianModel(prefix='lorentz{}_'.format(ii))

            params=model.make_params()

            return model, params

        def _search_end_of_dip(self, direction, data, peak_arg, start_arg, end_arg, sigma_threshold, minimal_threshold, make_prints):
            """
            data has to be offset bereinigt
            """
            absolute_min  = data[peak_arg]

            if direction == 'left':
                mult = -1
                sigma_arg=start_arg
            elif direction == 'right':
                mult = +1
                sigma_arg=end_arg
            else:
                print('No valid direction in search end of peak')
            ii=0

            #if the minimum is at the end set this as boarder
            if (peak_arg != start_arg and direction=='left' or
                peak_arg != end_arg   and direction=='right'):
                while True:
                    # if no minimum can be found decrease threshold
                    if ((peak_arg-ii<start_arg and direction == 'left') or
                        (peak_arg+ii>end_arg   and direction=='right')):
                        sigma_threshold*=0.9
                        ii=0
                        if make_prints:
                            print('h1 sigma_threshold',sigma_threshold)

                    #if the dip is always over threshold the end is as
                    # set before
                    if abs(sigma_threshold/absolute_min)<abs(minimal_threshold):
                        if make_prints:
                            print('h2')
                        break

                     #check if value was changed and search is finished
                    if ((sigma_arg == start_arg and direction == 'left') or
                        (sigma_arg == end_arg   and direction=='right')):
                        # check if if value is lower as threshold this is the
                        # searched value
                        if make_prints:
                            print('h3')
                        if abs(data[peak_arg+(mult*ii)])<abs(sigma_threshold):
                            # value lower than threshold found - left end found
                            sigma_arg=peak_arg+(mult*ii)
                            if make_prints:
                                print('h4')
                            break
                    ii+=1

            # in this case the value is the last index and should be search set
            # as right argument
            else:
                if make_prints:
                    print('neu h10')
                sigma_arg=peak_arg

            return sigma_threshold,sigma_arg


        def _search_double_dip(self, x_axis, data, threshold_fraction=0.3, minimal_threshold=0.01, sigma_threshold_fraction=0.3, make_prints=False):
            """ This method searches for a double dip. There are three values which can be set in order to adjust
            the search. A threshold which defines when  a minimum is a dip,
            this threshold is then lowered if no dip can be found until the
            minimal threshold which sets the absolute boarder and a
            sigma_threshold_fraction which defines when the

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values
            @param float threshold_fraction: x values
            @param float minimal_threshold: x values
            @param float sigma_threshold_fraction: x values


            @return int error: error code (0:OK, -1:error)
            @return int sigma0_argleft: index of left side of 1st peak
            @return int dip0_arg: index of max of 1st peak
            @return int sigma0_argright: index of right side of 1st peak
            @return int sigma1_argleft: index of left side of 2nd peak
            @return int dip1_arg: index of max side of 2nd peak
            @return int sigma1_argright: index of right side of 2nd peak
            """

            if sigma_threshold_fraction is None:
                sigma_threshold_fraction=threshold_fraction

            error=0

            #first search for absolute minimum
            absolute_min=data.min()
            absolute_argmin=data.argmin()

            #adjust thresholds
            threshold=threshold_fraction*absolute_min
            sigma_threshold=sigma_threshold_fraction*absolute_min

            dip0_arg = absolute_argmin

            # ====== search for the left end of the dip ======

            sigma_threshold, sigma0_argleft = self._search_end_of_dip(
                                     direction='left',
                                     data=data,
                                     peak_arg = absolute_argmin,
                                     start_arg = 0,
                                     end_arg = len(data)-1,
                                     sigma_threshold = sigma_threshold,
                                     minimal_threshold = minimal_threshold,
                                     make_prints= make_prints)

            if make_prints:
                print('Left sigma of main peak: ',x_axis[sigma0_argleft])

            # ====== search for the right end of the dip ======
            # reset sigma_threshold

            sigma_threshold, sigma0_argright = self._search_end_of_dip(
                                     direction='right',
                                     data=data,
                                     peak_arg = absolute_argmin,
                                     start_arg = 0,
                                     end_arg = len(data)-1,
                                     sigma_threshold = sigma_threshold_fraction*absolute_min,
                                     minimal_threshold = minimal_threshold,
                                     make_prints= make_prints)

            if make_prints:
                print('Right sigma of main peak: ',x_axis[sigma0_argright])

            # ======== search for second lorentzian dip ========
            left_index=int(0)
            right_index=len(x_axis)-1

            mid_index_left=sigma0_argleft
            mid_index_right=sigma0_argright

            # if main first dip covers the whole left side search on the right
            # side only
            if mid_index_left==left_index:
                if make_prints:
                    print('h11', left_index,mid_index_left,mid_index_right,right_index)
                #if one dip is within the second they have to be set to one
                if mid_index_right==right_index:
                    dip1_arg=dip0_arg
                else:
                    dip1_arg=data[mid_index_right:right_index].argmin()+mid_index_right

            #if main first dip covers the whole right side search on the left
            # side only
            elif mid_index_right==right_index:
                if make_prints:
                    print('h12')
                #if one dip is within the second they have to be set to one
                if mid_index_left==left_index:
                    dip1_arg=dip0_arg
                else:
                    dip1_arg=data[left_index:mid_index_left].argmin()

            # search for peak left and right of the dip
            else:
                while True:
                    #set search area excluding the first dip
                    left_min=data[left_index:mid_index_left].min()
                    left_argmin=data[left_index:mid_index_left].argmin()
                    right_min=data[mid_index_right:right_index].min()
                    right_argmin=data[mid_index_right:right_index].argmin()

                    if abs(left_min) > abs(threshold) and \
                       abs(left_min) > abs(right_min):
                        if make_prints:
                            print('h13')
                        # there is a minimum on the left side which is higher
                        # than the minimum on the right side
                        dip1_arg = left_argmin+left_index
                        break
                    elif abs(right_min)>abs(threshold):
                        # there is a minimum on the right side which is higher
                        # than on left side
                        dip1_arg=right_argmin+mid_index_right
                        if make_prints:
                            print('h14')
                        break
                    else:
                        # no minimum at all over threshold so lowering threshold
                        #  and resetting search area
                        threshold*=0.9
                        left_index=int(0)
                        right_index=len(x_axis)-1
                        mid_index_left=sigma0_argleft
                        mid_index_right=sigma0_argright
                        if make_prints:
                            print('h15')
                        #if no second dip can be found set both to same value
                        if abs(threshold/absolute_min)<abs(minimal_threshold):
                            if make_prints:
                                print('h16')
                            self.logMsg('threshold to minimum ratio was too '
                                        'small to estimate two minima. So both '
                                        'are set to the same value',
                                        msgType='message')
                            error=-1
                            dip1_arg=dip0_arg
                            break

            # if the dip is exactly at one of the boarders that means
            # the dips are most probably overlapping
            if dip1_arg == sigma0_argleft or dip1_arg == sigma0_argright:
                print('Dips are overlapping')
                distance_left  = abs(dip0_arg - sigma0_argleft)
                distance_right = abs(dip0_arg - sigma0_argright)
                sigma1_argleft = sigma0_argleft
                sigma1_argright = sigma0_argright
                if distance_left > distance_right:
                    dip1_arg = dip0_arg - abs(distance_left-distance_right)
                elif distance_left < distance_right:
                    dip1_arg = dip0_arg + abs(distance_left-distance_right)
                else:
                    dip1_arg = dip0_arg
                print(distance_left,distance_right,dip1_arg)
            else:
                # if the peaks are not overlapping search for left and right
                # boarder of the dip

                # ====== search for the right end of the dip ======
                sigma_threshold, sigma1_argleft = self._search_end_of_dip(
                                         direction='left',
                                         data=data,
                                         peak_arg = dip1_arg,
                                         start_arg = 0,
                                         end_arg = len(data)-1,
                                         sigma_threshold = sigma_threshold_fraction*absolute_min,
                                         minimal_threshold = minimal_threshold,
                                         make_prints= make_prints)

                # ====== search for the right end of the dip ======
                sigma_threshold, sigma1_argright = self._search_end_of_dip(
                                         direction='right',
                                         data=data,
                                         peak_arg = dip1_arg,
                                         start_arg = 0,
                                         end_arg = len(data)-1,
                                         sigma_threshold = sigma_threshold_fraction*absolute_min,
                                         minimal_threshold = minimal_threshold,
                                         make_prints= make_prints)

            return error, sigma0_argleft, dip0_arg, sigma0_argright, sigma1_argleft, dip1_arg, sigma1_argright


        def estimate_double_lorentz(self, x_axis=None, data=None,
                                    threshold_fraction=0.3,
                                    minimal_threshold=0.01,
                                    sigma_threshold_fraction=0.3):
            """ This method provides a lorentzian function.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values

            @return int error: error code (0:OK, -1:error)
            @return float lorentz0_amplitude: estimated amplitude of 1st peak
            @return float lorentz1_amplitude: estimated amplitude of 2nd peak
            @return float lorentz0_center: estimated x value of 1st maximum
            @return float lorentz1_center: estimated x value of 2nd maximum
            @return float lorentz0_sigma: estimated sigma of 1st peak
            @return float lorentz1_sigma: estimated sigma of 2nd peak
            @return float offset: estimated offset
            """
            error=0
            # check if parameters make sense
            parameters=[x_axis,data]
            for var in parameters:
                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.', \
                                msgType='error')
                    error=-1
                elif len(np.shape(var))!=1:
                    self.logMsg('Given parameter is no one dimensional array.',
                                msgType='error')


            #set paraameters
            data_smooth,offset=self.find_offset_parameter(x_axis,data)

            data_level=data_smooth-offset

            #search for double lorentzian

            error, \
            sigma0_argleft, dip0_arg, sigma0_argright, \
            sigma1_argleft, dip1_arg , sigma1_argright = \
            self._search_double_dip(x_axis, data_level, threshold_fraction,
                                   minimal_threshold, sigma_threshold_fraction)



            if dip0_arg == dip1_arg:
                lorentz0_amplitude = data_level[dip0_arg]/2.
                lorentz1_amplitude = lorentz0_amplitude
            else:
                lorentz0_amplitude=data_level[dip0_arg]
                lorentz1_amplitude=data_level[dip1_arg]

            lorentz0_center = x_axis[dip0_arg]
            lorentz1_center = x_axis[dip1_arg]

            #Both sigmas are set to the same value
            numerical_integral_0=(np.sum(data_level[sigma0_argleft:sigma0_argright]) *
                               (x_axis[sigma0_argright] - x_axis[sigma0_argleft]) /
                                len(data_level[sigma0_argleft:sigma0_argright]))

            lorentz0_sigma = abs(numerical_integral_0 /
                                 (np.pi * lorentz0_amplitude) )

            numerical_integral_1=numerical_integral_0

            lorentz1_sigma = abs( numerical_integral_1
                                  / (np.pi * lorentz1_amplitude)  )

            #esstimate amplitude
            lorentz0_amplitude = -1*abs(lorentz0_amplitude*np.pi*lorentz0_sigma)
            lorentz1_amplitude = -1*abs(lorentz1_amplitude*np.pi*lorentz1_sigma)


            if lorentz1_center < lorentz0_center :
                lorentz0_amplitude_temp = lorentz0_amplitude
                lorentz0_amplitude = lorentz1_amplitude
                lorentz1_amplitude = lorentz0_amplitude_temp
                lorentz0_center_temp    = lorentz0_center
                lorentz0_center    = lorentz1_center
                lorentz1_center    = lorentz0_center_temp
                lorentz0_sigma_temp= lorentz0_sigma
                lorentz0_sigma     = lorentz1_sigma
                lorentz1_sigma     = lorentz0_sigma_temp


            return error, lorentz0_amplitude,lorentz1_amplitude, \
                   lorentz0_center,lorentz1_center, lorentz0_sigma, \
                   lorentz1_sigma, offset

        def make_double_lorentzian_fit(self, axis=None, data=None,
                                       add_parameters=None):
            """ This method performes a 1D lorentzian fit on the provided data.

            @param array [] axis: axis values
            @param array[]  x_data: data
            @param dictionary add_parameters: Additional parameters

            @return lmfit.model.ModelFit result: All parameters provided about
                                                 the fitting, like: success,
                                                 initial fitting values, best
                                                 fitting values, data with best
                                                 fit with given axis,...

            """

            error,              \
            lorentz0_amplitude, \
            lorentz1_amplitude, \
            lorentz0_center,    \
            lorentz1_center,    \
            lorentz0_sigma,     \
            lorentz1_sigma,     \
            offset              = self.estimate_double_lorentz(axis, data)

            model, params = self.make_multiple_lorentzian_model(no_of_lor=2)

            # Auxiliary variables:
            stepsize=axis[1]-axis[0]
            n_steps=len(axis)

            #Defining standard parameters
            #            (Name,                  Value,          Vary, Min,                        Max,                         Expr)
            params.add('lorentz0_amplitude', lorentz0_amplitude, True, None,                       -0.01,                       None)
            params.add('lorentz0_sigma',     lorentz0_sigma,     True, (axis[1]-axis[0])/2 ,       (axis[-1]-axis[0])*4,        None)
            params.add('lorentz0_center',    lorentz0_center,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None)
            params.add('lorentz1_amplitude', lorentz1_amplitude, True, None,                       -0.01,                       None)
            params.add('lorentz1_sigma',     lorentz1_sigma,     True, (axis[1]-axis[0])/2 ,       (axis[-1]-axis[0])*4,        None)
            params.add('lorentz1_center',    lorentz1_center,    True, (axis[0])-n_steps*stepsize, (axis[-1])+n_steps*stepsize, None)
            params.add('c',                  offset,             True, None,                       None,                        None)

            #redefine values of additional parameters
            if add_parameters is not None:
                params=self._substitute_parameter(parameters=params,
                                                 update_parameters=add_parameters)
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                result=model.fit(data, x=axis,params=params)
                self.logMsg('The double lorentzian fit did not '
                            'work:'+result.message,
                            msgType='message')

            return result

        ############################################################################
        #                                                                          #
        #                                N14 fitting                               #
        #                                                                          #
        ############################################################################

        def estimate_N14(self, x_axis=None, data=None):
            """ Provide an estimation of all fitting parameters for fitting the
            three equdistant lorentzian dips of the hyperfine interaction
            of a N14 nuclear spin. Here the splitting is set as an expression,
            if the splitting is not exactly 2.15MHz the fit will not work.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values

            @return lmfit.parameter.Parameters parameters: New object corresponding
                                                           parameters like offset,
                                                           the three sigma's, the
                                                           three amplitudes and centers

            """

            data_smooth_lorentz,offset=self.find_offset_parameter(x_axis,data)

            #filter should always have a length of approx linewidth 1MHz
            stepsize_in_x=1/((x_axis.max()-x_axis.min())/len(x_axis))
            lorentz=np.ones(int(stepsize_in_x)+1)
            x_filter=np.linspace(0,5*stepsize_in_x,5*stepsize_in_x)
            lorentz=np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/5),
                                            (x_filter >= len(x_filter)/5)*(x_filter<len(x_filter)*2/5),
                                            (x_filter >= len(x_filter)*2/5)*(x_filter<len(x_filter)*3/5),
                                            (x_filter >= len(x_filter)*3/5)*(x_filter<len(x_filter)*4/5),
                                            (x_filter >= len(x_filter)*4/5)], [1, 0,1,0,1])
            data_smooth = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(),mode='constant',cval=data_smooth_lorentz.max())

            parameters=Parameters()

            #            (Name,                  Value,          Vary, Min,                        Max,                         Expr)
            parameters.add('lorentz0_amplitude', value=data_smooth_lorentz.min()-offset,         max=-1e-6)
            parameters.add('lorentz0_center',    value=x_axis[data_smooth.argmin()]-2.15)
            parameters.add('lorentz0_sigma',     value=0.5,                                      min=0.01,    max=4.)
            parameters.add('lorentz1_amplitude', value=parameters['lorentz0_amplitude'].value,   max=-1e-6)
            parameters.add('lorentz1_center',    value=parameters['lorentz0_center'].value+2.15, expr='lorentz0_center+2.15')
            parameters.add('lorentz1_sigma',     value=parameters['lorentz0_sigma'].value,       min=0.01,  max=4.,expr='lorentz0_sigma')
            parameters.add('lorentz2_amplitude', value=parameters['lorentz0_amplitude'].value,   max=-1e-6)
            parameters.add('lorentz2_center',    value=parameters['lorentz1_center'].value+2.15, expr='lorentz0_center+4.3')
            parameters.add('lorentz2_sigma',     value=parameters['lorentz0_sigma'].value,       min=0.01,  max=4.,expr='lorentz0_sigma')
            parameters.add('c',                  value=offset)

            return parameters


        def make_N14_fit(self, axis=None, data=None, add_parameters=None):
            """ This method performes a fit on the provided data where a N14
            hyperfine interaction of 2.15 MHz is taken into accound.

            @param array [] axis: axis values
            @param array[]  x_data: data
            @param dictionary add_parameters: Additional parameters

            @return lmfit.model.ModelFit result: All parameters provided about
                                                 the fitting, like: success,
                                                 initial fitting values, best
                                                 fitting values, data with best
                                                 fit with given axis,...

            """

            parameters=self.estimate_N14(axis, data)

            # redefine values of additional parameters
            if add_parameters is not None:
                parameters=self._substitute_parameter(parameters=parameters,
                                                      update_parameters=add_parameters)

            mod,params = self.make_multiple_lorentzian_model(no_of_lor=3)

            result=mod.fit(data=data, x=axis, params=parameters)


            return result

        ############################################################################
        #                                                                          #
        #                               N15 fitting                                #
        #                                                                          #
        ############################################################################

        def estimate_N15(self, x_axis=None, data=None):
            """ This method provides an estimation of all fitting parameters for
            fitting the three equdistant lorentzian dips of the hyperfine interaction
            of a N15 nuclear spin. Here the splitting is set as an expression, if the
            splitting is not exactly 3.03MHz the fit will not work.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values

            @return lmfit.parameter.Parameters parameters: New object corresponding
                                                           parameters like offset,
                                                           the three sigma's, the
                                                           three amplitudes and centers

            """

            data_smooth_lorentz,offset=self.find_offset_parameter(x_axis,data)

            hf_splitting=3.03
            #filter should always have a length of approx linewidth 1MHz
            stepsize_in_x=1/((x_axis.max()-x_axis.min())/len(x_axis))
            lorentz=np.zeros(int(stepsize_in_x)+1)
            x_filter=np.linspace(0,4*stepsize_in_x,4*stepsize_in_x)
            lorentz=np.piecewise(x_filter, [(x_filter >= 0)*(x_filter<len(x_filter)/4),
                                            (x_filter >= len(x_filter)/4)*(x_filter<len(x_filter)*3/4),
                                            (x_filter >= len(x_filter)*3/4)], [1, 0,1])
            data_smooth = filters.convolve1d(data_smooth_lorentz, lorentz/lorentz.sum(),mode='constant',cval=data_smooth_lorentz.max())

    #            plt.plot(x_axis[:len(lorentz)],lorentz)
    #            plt.show()

    #            plt.plot(x_axis,data)
    #            plt.plot(x_axis,data_smooth)
    #            plt.plot(x_axis,data_smooth_lorentz)
    #            plt.show()

            parameters=Parameters()

            parameters.add('lorentz0_amplitude',value=data_smooth.min()-offset,max=-1e-6)
            parameters.add('lorentz0_center',value=x_axis[data_smooth.argmin()]-hf_splitting/2.)
            parameters.add('lorentz0_sigma',value=0.5,min=0.01,max=4.)
            parameters.add('lorentz1_amplitude',value=parameters['lorentz0_amplitude'].value,max=-1e-6)
            parameters.add('lorentz1_center',value=parameters['lorentz0_center'].value+hf_splitting,expr='lorentz0_center+3.03')
            parameters.add('lorentz1_sigma',value=parameters['lorentz0_sigma'].value,min=0.01,max=4.,expr='lorentz0_sigma')
            parameters.add('c',value=offset)

            return parameters


        def make_N15_fit(self, axis=None, data=None, add_parameters=None):
            """ This method performes a fit on the provided data where a N14
            hyperfine interaction of 3.03 MHz is taken into accound.

            @param array [] axis: axis values
            @param array[]  x_data: data
            @param dictionary add_parameters: Additional parameters

            @return lmfit.model.ModelFit result: All parameters provided about
                                                 the fitting, like: success,
                                                 initial fitting values, best
                                                 fitting values, data with best
                                                 fit with given axis,...

            """

            parameters=self.estimate_N15(axis,data)

            #redefine values of additional parameters
            if add_parameters is not None:
                parameters=self._substitute_parameter(parameters=parameters,
                                                     update_parameters=add_parameters)

            mod,params = self.make_multiple_lorentzian_model(no_of_lor=2)

            result=mod.fit(data=data, x=axis, params=parameters)


            return result

        ############################################################################
        #                                                                          #
        #                               Sinus fitting                              #
        #                                                                          #
        ############################################################################

        def estimate_sine(self, x_axis=None, data=None):
            """ This method provides a sine function.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to x values

            @return int error: error code (0:OK, -1:error)
            @return float amplitude: estimated amplitude
            @return float omega: estimated period of the sine
            @return float shift: estimated phase shift
            @return float decay: estimated decay of the curve
            @return float offset: estimated offset
            """

            error = 0

            # check if parameters make sense

            parameters=[x_axis,data]
            for var in parameters:
                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.', msgType='error')
                    error=-1
                elif len(np.shape(var))!=1:
                    self.logMsg('Given parameter is no one dimensional '
                                'array.', msgType='error')
                    error=-1

            # set parameters

            offset = np.average(data)
            data_level = data - offset
            amplitude = max(data_level.max(),np.abs(data_level.min()))
            fourier = np.fft.fft(data_level)
            stepsize = x_axis[1]-x_axis[0]
            freq = np.fft.fftfreq(data_level.size,stepsize)
            tmp = freq,np.log(fourier)
            omega = 1/(np.abs(tmp[0][tmp[1].argmax()]))
            shift_tmp = (offset-data[0])/amplitude
            shift = np.arccos(shift_tmp)

            # TODO: Improve decay estimation
            if len(data) > omega/stepsize * 2.5:
                pos01 = int((1-shift/(np.pi**2)) * omega/(2*stepsize))
                pos02 = pos01 + int(omega/stepsize)
                # print(pos01,pos02,data[pos01],data[pos02])
                decay = np.log(data[pos02]/data[pos01])/omega
                # decay = - np.log(0.2)/x_axis[-1]
            else:
                decay = 0.0

            return amplitude, offset, shift, omega, decay

        # define objective function: returns the array to be minimized
        def fcn2min(self,params, x, data):
            """ model decaying sine wave, subtract data"""
            v = params.valuesdict()

            model = v['amplitude'] * \
                    np.sin(x * 1/v['omega']*np.pi*2 + v['shift']) * \
                    np.exp(-x*v['decay']) + v['offset']

            return model - data

        def make_sine_fit(self, axis=None, data=None, add_parameters=None):
            """ This method performes a sine fit on the provided data.

            @param array[] axis: axis values
            @param array[]  data: data
            @param dictionary add_parameters: Additional parameters

            @return result: All parameters provided about the fitting, like:
                            success,
                            initial fitting values, best fitting values, data
                            with best fit with given axis,...
            @return float fit_x: x values to plot the fit
            @return float fit_y: y values to plot the fit
            """


            amplitude,  \
            offset,     \
            shift,      \
            omega,      \
            decay       = self.estimate_sine(axis, data)

            params = Parameters()

            #Defining standard parameters
            #               (Name,        Value,     Vary, Min,  Max,  Expr)
            params.add_many(('amplitude', amplitude, True, None, None, None),
                            ('offset',    offset,    True, None, None, None),
                            ('shift',     shift,     True, None, None, None),
                            ('omega',     omega,     True, None, None, None),
                            ('decay',     decay,     True, None, None, None))


            #redefine values of additional parameters
            if add_parameters is not None:
                params=self._substitute_parameter(parameters=params,
                                                 update_parameters=add_parameters)
            try:
                result = minimize(self.fcn2min, params, args=(axis, data))
            except:
                result = minimize(self.fcn2min, params, args=(axis, data))
                self.logMsg('The sine fit did not work. Error '
                            'message:'+result.message,
                            msgType='message')

            fit_y = data + result.residual
            fit_x = axis


            return result, fit_x, fit_y

    ############################################################################
    #                                                                          #
    #           Excitation power - fluorescence dependency                     #
    #                                                                          #
    ############################################################################

        @staticmethod
        def powerfluorescence_function(x, I_saturation, P_saturation):
            """
            Function to describe the fluorescence depending on excitation power
            @param x: variable variable - Excitation pwer
            @param I_saturation: Saturation Intensity
            @param P_saturation: Saturation power

            @return: powerfluorescence function: for using it as a model
            """

            return I_saturation * (x / (x + P_saturation))


        def make_powerfluorescence_model(self):
            """ This method creates a model of the fluorescence depending on excitation power with an linear offset.

            @return tuple: (object model, object params)

            Explanation of the objects:
                object lmfit.model.CompositeModel model:
                    A model the lmfit module will use for that fit. Here a
                    gaussian model. Returns an object of the class
                    lmfit.model.CompositeModel.

                object lmfit.parameter.Parameters params:
                    It is basically an OrderedDict, so a dictionary, with keys
                    denoting the parameters as string names and values which are
                    lmfit.parameter.Parameter (without s) objects, keeping the
                    information about the current value.

            For further information have a look in:
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
            """
            mod_sat = Model(self.powerfluorescence_function)

            model = mod_sat + LinearModel()

            params = model.make_params()

            return model, params

        def make_powerfluorescence_fit(self, axis=None, data=None, add_parameters=None):
            """ This method performes a fit of the fluorescence depending on power
                on the provided data.

            @param array[] axis: axis values
            @param array[]  x_data: data
            @param dict add_parameters: Additional parameters

            @return object result: lmfit.model.ModelFit object, all parameters
                                   provided about the fitting, like: success,
                                   initial fitting values, best fitting values, data
                                   with best fit with given axis,...
            """

            mod_final, params = self.make_powerfluorescence_model()

            error, params = self.estimate_powerfluorescence(axis, data, params)


            # overwrite values of additional parameters
            if add_parameters is not None:
                params = self._substitute_parameter(parameters=params,
                                                   update_parameters=add_parameters)
            try:
                result = mod_final.fit(data, x=axis, params=params)
            except:
                self.logMsg('The 1D gaussian fit did not work.',
                            msgType='message')
                result = mod_final.fit(data, x=axis, params=params)
                print(result.message)

            return result

        def estimate_powerfluorescence(self, x_axis=None, data=None, params=None):
            """ This method provides a one dimensional gaussian function.

            @param array x_axis: x values
            @param array data: value of each data point corresponding to x values
            @param Parameters object params: object includes parameter dictionary which can be set

            @return tuple (error, params):

            Explanation of the return parameter:
                int error: error code (0:OK, -1:error)
                Parameters object params: set parameters of initial values
            """

            error = 0
            # check if parameters make sense
            parameters = [x_axis, data]
            for var in parameters:
                if not isinstance(var, (frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.',
                                msgType='error')
                    error = -1
                elif len(np.shape(var)) != 1:
                    self.logMsg('Given parameter is no one dimensional array.',
                                msgType='error')
                    error = -1
            if not isinstance(params, Parameters):
                self.logMsg('Parameters object is not valid in estimate_gaussian.',
                            msgType='error')
                error = -1

            #TODO: some estimated values should be input here

            return error, params


##############################################################################
##############################################################################

                        #Testing routines

##############################################################################
##############################################################################  

        def N15_testing(self):
            x = np.linspace(2840, 2860, 101)
                
            mod,params = self.make_multiple_lorentzian_model(no_of_lor=2)
#            print('Parameters of the model',mod.param_names)
            
            p=Parameters()
            
            p.add('lorentz0_amplitude',value=-35)
            p.add('lorentz0_center',value=2850+abs(np.random.random(1)*8))
            p.add('lorentz0_sigma',value=abs(np.random.random(1)*1)+0.5)
            p.add('lorentz1_amplitude',value=-20)
            p.add('lorentz1_center',value=p['lorentz0_center'].value+3.03)
            p.add('lorentz1_sigma',value=p['lorentz0_sigma'].value)
            p.add('c',value=100.)
            
            data_noisy=(mod.eval(x=x,params=p) 
                                    + 1.5*np.random.normal(size=x.shape))
            
            result=self.make_N15_fit(x,data_noisy)
            print(result.best_values['lorentz0_center'])            
            plt.plot(x,data_noisy)
            plt.plot(x,result.init_fit,'-y')
            plt.plot(x,result.best_fit,'-r')
            plt.show()
            
        def N14_testing(self):
            x = np.linspace(2850, 2860, 101)
                
            mod,params = self.make_multiple_lorentzian_model(no_of_lor=3)
#            print('Parameters of the model',mod.param_names)
            
            p=Parameters()
            
            p.add('lorentz0_amplitude',value=-35)
            p.add('lorentz0_center',value=2850+abs(np.random.random(1)*8))
            p.add('lorentz0_sigma',value=abs(np.random.random(1)*1)+0.5)
            p.add('lorentz1_amplitude',value=-20)
            p.add('lorentz1_center',value=p['lorentz0_center'].value+2.15)
            p.add('lorentz1_sigma',value=p['lorentz0_sigma'].value)
            p.add('lorentz2_amplitude',value=-10.)
            p.add('lorentz2_center',value=p['lorentz1_center'].value+2.15)
            p.add('lorentz2_sigma',value=p['lorentz0_sigma'].value)
            p.add('c',value=100.)
            
            data_noisy=(mod.eval(x=x,params=p) 
                                    + 2*np.random.normal(size=x.shape))
            
            result=self.make_N14_fit(x,data_noisy)
#            print(result.best_values['lorentz0_center'])            
            plt.plot(x,data_noisy)
            plt.plot(x,result.init_fit,'-y')
            plt.plot(x,result.best_fit,'-r')
            plt.show()


            

                                    
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
            data= self.twoD_gaussian_model(x=axes,amplitude=amplitude,x_zero=x_zero,y_zero=y_zero,sigma_x=sigma_x,sigma_y=sigma_y,theta=theta_here, offset=offset)
            data+=50000*np.random.random_sample(np.shape(data))
            
            gmod,params = self.make_twoD_gaussian_model()
            
            para=Parameters()
#            para.add('theta',vary=False)
#            para.add('x_zero',expr='0.5*y_zero')
#            para.add('sigma_x',min=0.2*((92.-90.)/11.) ,           max=   10*(x[-1]-y[0]) )
#            para.add('sigma_y',min=0.2*((15.-13.)/12.) ,           max=   10*(y[-1]-y[0])) 
#            para.add('x_zero',value=40,min=50,max=100)
            
            result=self.make_twoD_gaussian_fit(axis=axes,data=data,add_parameters=para)
            
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
                
                mod,params = self.make_multiple_lorentzian_model(no_of_lor=2)
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
                result=self.make_double_lorentzian_fit(axis=x,data=data_noisy,add_parameters=para)
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
                self._search_double_dip(x, data_level,make_prints=True)

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
                start=100000
                stop=400000
                num_points=int((stop-start)/2000)
                x = np.linspace(start, stop, num_points)
                
                mod,params = self.make_multiple_gaussian_model(no_of_gauss=2)
    #            print('Parameters of the model',mod.param_names)
                
                p=Parameters()
                calculate_alex_model=True
                if calculate_alex_model==False:
    #                #============ Create data ==========
                    self.dist = 'dark_bright_gaussian'
    
                    self.mean_signal = 260*1000
                    self.contrast = 0.3
                    self.mean_signal2 = self.mean_signal - self.contrast*self.mean_signal
                    self.noise_amplitude = self.mean_signal*0.1
            
                    self.life_time_bright = 0.08 # 60 millisecond
                    self.life_time_dark    = 0.04 # 40 milliseconds
                    
                    # needed for the life time simulation
                    self.current_dec_time = self.life_time_bright
                    self.curr_state_b = True
                    self.total_time = 0.0
                    
                    start=time.time()
                    data=self.get_counter(500)
                    print('time to create data',time.time()-start)
                    
                    plt.hist(data[0,:],20)
                    plt.show()
                    
                amplitude=75000+np.random.random(1)*50000
                sigma0=25000+np.random.random(1)*20000
                sigma1=25000+np.random.random(1)*20000
                splitting=abs(np.random.random(1)*300000)
                p.add('gaussian0_amplitude',value=amplitude)
                p.add('gaussian0_center',value=160000)
                p.add('gaussian0_sigma',value=sigma0)
                p.add('gaussian1_amplitude',value=amplitude*1.5)
                p.add('gaussian1_center',value=100000+splitting)
                p.add('gaussian1_sigma',value=sigma1)
                p.add('c',value=0.)

                data_noisy=(mod.eval(x=x,params=p)
                                        + 0.3*np.random.normal(size=x.shape))

#                np.savetxt('data',data_noisy)

#                data_noisy=np.loadtxt('data')
#                para=Parameters()
#                result=self.make_double_gaussianian_fit(axis=x,data=data_noisy,add_parameters=para)
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

                result=self.make_double_gaussian_fit(x,data_noisy,
                                        threshold_fraction=threshold_fraction, 
                                        minimal_threshold=minimal_threshold, 
                                        sigma_threshold_fraction=sigma_threshold_fraction)
                                        
                plt.plot((result.init_values['gaussian0_center'], result.init_values['gaussian0_center']), ( data_noisy.min() ,data_noisy.max()), 'r-')
                plt.plot((result.init_values['gaussian1_center'], result.init_values['gaussian1_center']), ( data_noisy.min() ,data_noisy.max()), 'r-')                                    
                print(result.init_values['gaussian0_center'],result.init_values['gaussian1_center'])
#                gaus=gaussian(20,10)
#                data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum(),mode='mirror')
#                data_der=np.gradient(data_smooth)
#                print(result.fit_report())
#                print(result.message)
#                print(result.success)
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

        def get_counter(self,samples=None):
            """ Returns the current counts per second of the counter.
    
            @param int samples: if defined, number of samples to read in one go
    
            @return float: the photon counts per second
            """
    
            count_data = np.empty([2,samples], dtype=np.uint32) # count data will be written here in the NumPy array
            
            self._clock_frequency=100

            
            timestep = 1./self._clock_frequency*samples
            
            for i in range(samples):
    
                if self.dist == 'single_gaussian':
                    count_data[0][i] = np.random.normal(self.mean_signal, self.noise_amplitude/2)
    
                elif self.dist == 'dark_bright_gaussian':
    
                    self.total_time = self.total_time + timestep
    
                    if self.total_time > self.current_dec_time:
                        if self.curr_state_b:
                            self.curr_state_b = False
                            self.current_dec_time = np.random.exponential(self.life_time_dark)
                            count_data[0][i] = np.random.poisson(self.mean_signal)
                        else:
                            self.curr_state_b = True
                            self.current_dec_time = np.random.exponential(self.life_time_bright)
                        self.total_time = 0.0
    
                    count_data[0][i] = np.random.normal(self.mean_signal, self.noise_amplitude)*self.curr_state_b + \
                                       np.random.normal(self.mean_signal2, self.noise_amplitude)*(1-self.curr_state_b)
    
                elif self.dist == 'uniform':
                    count_data[0][i] = self.mean_signal + random.uniform(-self.noise_amplitude/2, self.noise_amplitude/2)
    
                elif self.dist == 'exponential':
                    count_data[0][i] = np.random.exponential(self.mean_signal)
    
                elif self.dist == 'single_poisson':
                    count_data[0][i] = np.random.poisson(self.mean_signal)
    
                elif self.dist == 'dark_bright_poisson':
                    self.total_time = self.total_time + timestep
    
                    if self.total_time > self.current_dec_time:
                        if self.curr_state_b:
                            self.curr_state_b = False
                            self.current_dec_time = np.random.exponential(self.life_time_dark)
                            count_data[0][i] = np.random.poisson(self.mean_signal)
                        else:
                            self.curr_state_b = True
                            self.current_dec_time = np.random.exponential(self.life_time_bright)
                        self.total_time = 0.0
    
                    count_data[0][i] = np.random.poisson(self.mean_signal)*self.curr_state_b + np.random.poisson(self.mean_signal2)*(1-self.curr_state_b)
    
                else:
                    # make uniform as default
                    count_data[0][i] = self.mean_signal + random.uniform(-self.noise_amplitude/2, self.noise_amplitude/2)
    
    
            time.sleep(1./self._clock_frequency*samples)
    
            return count_data

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
            
test=FitLogic()
#test.twoD_testing()
test.double_gaussian_testing()
#test.double_lorentzian_testing()
#test.powerfluorescence_testing()
