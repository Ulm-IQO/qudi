# -*- coding: utf-8 -*-
# unstable: Jochen Scheuer

from logic.generic_logic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.mutex import Mutex
from collections import OrderedDict

from lmfit.models import Model, ConstantModel, LorentzianModel, GaussianModel
from lmfit import Parameters, minimize
from scipy.signal import gaussian
from scipy.ndimage import filters

import numpy as np
import scipy.optimize as opt#, scipy.stats


#FIXME: In general is it needed for any purposes to use weighting?
#FIXME: Don't understand exactly when you return error code...

"""
General procedure to create new fitting routines:

A fitting routine consists out of three major parts:
    1. a (mathematical) Model you have for the passed data
    2. an Estimator, which can extract from the passed data initial values for
       the fitting routine.
    3. The actual fit algorithm

The power of that general splitting is that you can write pretty independent
fit algorithms, but their efficiency will (very often) rely on the quality of
the estimator.
"""



class FitLogic(GenericLogic):
    """
    UNSTABLE:Jochen Scheuer
    This is the fitting class where fit functions are defined and methods are
    implemented to process the data.

    Here fit functions and estimators are provided, so for every function there
    is a callable function (gaussian_function), a corresponding estimator
    (gaussian_estimator) and a method (make_gaussian_fit) which executes the
    fit.

    """
    _modclass = 'fitlogic'
    _modtype = 'logic'
    ## declare connectors
    _out = {'fitlogic': 'FitLogic'}

    def __init__(self, manager, name, config, **kwargs):
        ## declare actions for state transitions
        state_actions = {'onactivate':self.activation,
                         'ondeactivate':self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)
        #locking for thread safety
        self.lock = Mutex()

    def activation(self,e):
        """ Initialisation performed during activation of the module.

        @param object e: Event class object from Fysom.
                         An object created by the state machine module Fysom,
                         which is connected to a specific event (have a look in
                         the Base Class). This object contains the passed event,
                         the state before the event happened and the destination
                         of the state which should be reached after the event
                         had happened.
        """

        pass

    def deactivation(self,e):
        pass


    ############################################################################
    #                                                                          #
    #                             General methods                              #
    #                                                                          #
    ############################################################################

        def substitute_parameter(self, parameters=None, update_parameters=None):
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
                    store_value=parameters[para].value

                    # the Parameter object changes the value, min and max when the
                    # value is called therefore the parameters have to be saved from
                    # the reseted Parameter object therefore the Parameters have to be
                    # saved also here

                    para_temp=update_parameters
                    if para_temp[para].value!=None:
                        value_new=True
                        value_value=para_temp[para].value
                    else:
                        value_new=False

                    para_temp=update_parameters
                    if para_temp[para].min!=None:
                        min_new=True
                        min_value=para_temp[para].min
                    else:
                        min_new=False

                    para_temp=update_parameters
                    if para_temp[para].max!=None:
                        max_new=True
                        max_value=para_temp[para].max
                    else:
                        max_new=False

                    # vary is set by default to True
                    parameters[para].vary=update_parameters[para].vary

                    # if the min, max and expression and value are new overwrite
                    # them here

                    if min_new:
                        parameters[para].min=update_parameters[para].min

                    if max_new:
                        parameters[para].max=update_parameters[para].max

                    if update_parameters[para].expr!=None:
                        parameters[para].expr=update_parameters[para].expr

                    if value_new:
                        parameters[para].value=value_value

                    # if the min or max are changed they overwrite the value
                    # therefore here the values have to be reseted to the initial
                    # value also when no new value was set in the beginning

                    if min_new:
                        # in case the value is 0, devision by 0 has to be avoided
                        if parameters[para].value<1e-12:
                            if abs((min_value+1.)/(parameters[para].value+1.)-1.)<1e-12:
                                parameters[para].value=store_value
                        else:
                            if abs(min_value/parameters[para].value-1.)<1e-12:
                                parameters[para].value=store_value
                    if max_new:
                        # in case the value is 0, devision by 0 has to be avoided
                        if parameters[para].value<1e-12:
                            if abs((max_value+1.)/(parameters[para].value+1.)-1.)<1e-12:
                                parameters[para].value=store_value
                        else:
                            if abs(max_value/parameters[para].value-1.)<1e-12:
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

        model=GaussianModel()+ConstantModel()
        params=model.make_params()

        return model,params

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

        error,      \
        amplitude,  \
        x_zero,     \
        sigma,      \
        offset      = self.estimate_gaussian(axis, data)

        mod_final,params = self.make_gaussian_model()

        #auxiliary variables
        stepsize=abs(axis[1]-axis[0])
        n_steps=len(axis)

        #Defining standard parameters
        #                  (Name,       Value,  Vary,         Min,                    Max,                                Expr)
        params.add_many(('amplitude',amplitude, True,         100,                    data.max()*sigma*np.sqrt(2*np.pi),  None),
                       (  'sigma',    sigma,    True,     1*(stepsize) ,              3*(axis[-1]-axis[0]),               None),
                       (  'center',  x_zero,    True, (axis[0])-n_steps*stepsize,     (axis[-1])+n_steps*stepsize,        None),
                       (    'c',      offset,   True,         100,                    data.max(),                         None))


        #redefine values of additional parameters
        if add_parameters!=None:
            params=self.substitute_parameter(parameters=params,
                                             update_parameters=add_parameters)
        try:
            result=mod_final.fit(data, x=axis,params=params)
        except:
            self.logMsg('The 1D gaussian fit did not work.',
                        msgType='message')
            result=mod_final.fit(data, x=axis,params=params)
            print(result.message)

        return result

    def estimate_gaussian(self, x_axis=None, data=None):
        """ This method provides a one dimensional gaussian function.

        @param array x_axis: x values
        @param array data: value of each data point corresponding to x values

        @return tuple (error, amplitude, x_zero, sigma_x, offset):

        Explanation of the return parameter:
            int error: error code (0:OK, -1:error)
            float amplitude: estimated amplitude
            float x_zero: estimated x value of maximum
            float sigma_x: estimated standard deviation in x direction
            float offset: estimated offset
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
                self.logMsg('Given parameter is no one dimensional array.', \
                            msgType='error')
        #set paraameters
        x_zero=x_axis[np.argmax(data)]
        sigma = (x_axis.max()-x_axis.min())/3.
        amplitude=(data.max()-data.min())*(sigma*np.sqrt(2*np.pi))
        offset=data.min()

        return error, amplitude, x_zero, sigma, offset


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
        offset      = self.twoD_gaussian_estimator(x_axis=x_axis,
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
        if add_parameters!=None:
            params=self.substitute_parameter(parameters=params,
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

        # check if parameters make sense
        #FIXME: Check for 2D matrix
        if not isinstance( x,(frozenset, list, set, tuple,\
                            np.ndarray)):
            self.logMsg('Given range of axes is no array type.',
                        msgType='error')

        parameters=[amplitude,x_zero,y_zero,sigma_x,sigma_y,theta,offset]
        for var in parameters:
            if not isinstance(var,(float,int)):
                self.logMsg('Given range of parameter is no float or int.',
                            msgType='error')

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
        if len(x_values)>=100.:
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
        if add_parameters!=None:
            params=self.substitute_parameter(parameters=params,
                                             update_parameters=add_parameters)
        try:
            result=model.fit(data, x=axis,params=params)
        except:
            result=model.fit(data, x=axis,params=params)
            self.logMsg('The 1D gaussian fit did not work. Error '
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

        if add_parameters!=None:
            params=self.substitute_parameter(parameters=params,
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


    def estimate_double_lorentz(self, x_axis=None, data=None):
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
        make_prints=False
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

        #first search for absolute minimum
        absolute_min=data_level.min()
        absolute_argmin=data_level.argmin()

        lorentz0_center=x_axis[absolute_argmin]
        lorentz0_amplitude=data_level.min()

        #TODO: make threshold,minimal_threshold and sigma_threshold value a
        # config variable

        #set thresholds
        self.threshold_fraction=0.3
        threshold=self.threshold_fraction*absolute_min
        self.minimal_threshold=0.01
        self.sigma_threshold_fraction=0.5
        sigma_threshold=self.sigma_threshold_fraction*absolute_min

#       search for the left end of the dip
        sigma_argleft=int(0)
        ii=0

        #if the minimum is at the end set this as boarder
        if absolute_argmin != 0:
            while True:

                # if no minimum can be found decrease threshold
                if absolute_argmin-ii<0:
                    sigma_threshold*=0.9
                    ii=0
                    if make_prints:
                        print('h1')

                #if the dip is alsways over threshold the end is the 0 as
                # set before
                if abs(sigma_threshold)<abs(threshold):
                    if make_prints:
                        print('h2')
                    break

                 #check if value was changed and search is finished
                if sigma_argleft==0:
                    # check if if value is lower as threshold this is the
                    # searched value
                    if make_prints:
                        print('h3')
                    if abs(data_level[absolute_argmin-ii])<abs(sigma_threshold):
                        sigma_argleft=absolute_argmin-ii
                        if make_prints:
                            print('sigma_argleft',x_axis[sigma_argleft])

                #if value is not zero the search was successful and finished
                else:
                    if make_prints:
                        print('h5')
                    break
                ii+=1

        #search for the right end of the dip
        sigma_argright=int(0)
        ii = 0

        #if the minimum is at the end set this as boarder
        if absolute_argmin != len(data)-1:
            while True:

                # if no minimum can be found decrease threshold
                if absolute_argmin+ii>len(data)-1:
                    sigma_threshold*=0.9
                    ii=0
                    if make_prints:
                        print('h6')
                # if the dip is alsways over threshold the end is the most
                # right index
                if abs(sigma_threshold)<abs(threshold):
                    sigma_argright=len(data)-1
                    if make_prints:
                        print('h7')
                    break

                #check if value was changed and search is finished
                if sigma_argright==0:

                    if make_prints:
                        print('h8')
                    # check if if value is lower as threshold this is the
                    # searched value
                    if abs(data_level[absolute_argmin+ii])<abs(sigma_threshold):
                        if make_prints:
                            print('h9')
                        sigma_argright=absolute_argmin+ii

                #if value is not zero the search was successful and finished
                else:
                    if make_prints:
                        print('sigma argright',x_axis[sigma_argright])
                    break
                ii+=1

        # in this case the value is the last index and should be search set
        # as right argument
        else:
            if make_prints:
                print('h10')
            sigma_argright=absolute_argmin

        numerical_integral_0=np.sum(data_level[sigma_argleft:sigma_argright]) * \
                           (x_axis[sigma_argright] - x_axis[sigma_argleft]) / len(data_level[sigma_argleft:sigma_argright])

        lorentz0_sigma = abs(numerical_integral_0 /
                             (np.pi * lorentz0_amplitude) )

#           ======== search for second lorentzian dip ========
        left_index=int(0)
        right_index=len(x_axis)-1

        mid_index_left=sigma_argleft
        mid_index_right=sigma_argright

        # if main first dip covers the whole left side search on the right
        # side only
        if sigma_argleft==left_index:
            if make_prints:
                print('h11', left_index,mid_index_left,mid_index_right,right_index)
            #if one dip is within the second they have to be set to one
            if sigma_argright==right_index:
                lorentz1_center=lorentz0_center
                lorentz0_amplitude/=2.
                lorentz1_amplitude=lorentz0_amplitude
            else:
                lorentz1_center=x_axis[data_level[mid_index_right:right_index].argmin()+
                                       mid_index_right]
                lorentz1_amplitude=data_level[mid_index_right:right_index].min()

        #if main first dip covers the whole right side search on the left
        # side only
        elif sigma_argright==right_index:
            if make_prints:
                print('h12')
            #if one dip is within the second they have to be set to one
            if sigma_argleft==left_index:
                lorentz1_center=lorentz0_center
                lorentz0_amplitude/=2.
                lorentz1_amplitude=lorentz0_amplitude
            else:
                lorentz1_amplitude=data_level[left_index:mid_index_left].min()
                lorentz1_center=x_axis[data_level[left_index:mid_index_left].argmin()]

        # search for peak left and right of the dip
        else:
            while True:
                #set search area excluding the first dip
                left_min=data_level[left_index:mid_index_left].min()
                left_argmin=data_level[left_index:mid_index_left].argmin()
                right_min=data_level[mid_index_right:right_index].min()
                right_argmin=data_level[mid_index_right:right_index].argmin()

                if abs(left_min) > abs(threshold) and \
                   abs(left_min) > abs(right_min):
                    if make_prints:
                        print('h13')
                    # there is a minimum on the left side which is higher
                    # than right side
                    lorentz1_amplitude=left_min
                    lorentz1_center=x_axis[left_argmin+left_index]
                    break
                elif abs(right_min)>abs(threshold):
                    # there is a minimum on the right side which is higher
                    # than on left side
                    lorentz1_amplitude=right_min
                    lorentz1_center=x_axis[right_argmin+mid_index_right]
                    if make_prints:
                        print('h14')
                    break
                else:
                    # no minimum at all over threshold so lowering threshold
                    #  and resetting search area
                    threshold=threshold*3./4.
                    left_index=int(0)
                    right_index=len(x_axis)-1
                    mid_index_left=sigma_argleft
                    mid_index_right=sigma_argright
                    if make_prints:
                        print('h15')
                    #if no second dip can be found set both to same value
                    if abs(threshold/absolute_min)<abs(self.minimal_threshold):
                        if make_prints:
                            print('h16')
                        self.logMsg('threshold to minimum ratio was too '
                                    'small to estimate two minima. So both '
                                    'are set to the same value',
                                    msgType='message')
                        error=-1
                        lorentz1_center=lorentz0_center
                        lorentz0_amplitude/=2.
                        lorentz1_amplitude=lorentz0_amplitude/2.
                        break


        numerical_integral_1=np.sum(data_level[sigma_argleft:sigma_argright]) * \
                           (x_axis[sigma_argright] - x_axis[sigma_argleft]) / len(data_level[sigma_argleft:sigma_argright])

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
        @param int no_of_lor: Number of lorentzians
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
        if add_parameters!=None:
            params=self.substitute_parameter(parameters=params,
                                             update_parameters=add_parameters)
        try:
            result=model.fit(data, x=axis,params=params)
        except:
            result=model.fit(data, x=axis,params=params)
            self.logMsg('The double lorentuab fit did not '
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
        parameters.add('lorentz0_amplitude', value=data_smooth_lorentz.min()-offset,        max=-1e-6)
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

        parameters=self.estimate_N14(axis,data)

        #redefine values of additional parameters
        if add_parameters!=None:
            parameters=self.substitute_parameter(parameters=parameters,
                                                 update_parameters=add_parameters)

        mod,params = self.make_multiple_lorentzian_model(no_of_lor=3)

        result=mod.fit(data=data,x=axis,params=parameters)


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
        if add_parameters!=None:
            parameters=self.substitute_parameter(parameters=parameters,
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
        if add_parameters != None:
            params=self.substitute_parameter(parameters=params,
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