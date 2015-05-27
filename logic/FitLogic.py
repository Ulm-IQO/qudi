# -*- coding: utf-8 -*-
# unstable: Jochen Scheuer

from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict

from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel

import numpy as np
import scipy.optimize as opt#, scipy.stats

#TODO:
#try smooth as estimator
#Missing functions:  
#                    -Double lorentian
#                    - N15
#                    - N14
#                    - C13 variabler


#FIXME: In general is it needed for any purposes to use weighting?
#FIXME: Don't understand exactly when you return error code...

class FitLogic(GenericLogic):        
        """
        UNSTABLE:Jochen Scheuer
        This is the fitting class where fit functions are defined and methods
        are implemented to process the data.
        
        Here fit functions and estimators are provided, so for every function
        there is a callable function (gaussian_function), a corresponding 
        estimator (gaussian_estimator) and a method (make_gaussian_fit) which 
        executes the fit.
        
        """
        
        def __init__(self, manager, name, config, **kwargs):
            ## declare actions for state transitions
            state_actions = {}
            GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
            self._modclass = 'fitlogic'
            self._modtype = 'logic'
    
            ## declare connectors
            
            self.connector['out']['fitlogic'] = OrderedDict()
            self.connector['out']['fitlogic']['class'] = 'FitLogic'
            
            #locking for thread safety
            self.lock = Mutex()
    
            self.logMsg('The following configuration was found.', 
                        msgType='status')

##############################################################################
##############################################################################
##############################################################################

    # the following two functions are needed for the ConfocalInterfaceDummy


##############################################################################
##############################################################################
##############################################################################


        def twoD_gaussian_function(self,x_data_tuple=None,amplitude=None,\
                                    x_zero=None, y_zero=None, sigma_x=None, \
                                    sigma_y=None, theta=None, offset=None):
                                        
            #FIXME: x_data_tuple: dimension of arrays
                                    
            """ This method provides a two dimensional gaussian function.
            
            @param (k,M)-shaped array x_data_tuple: x and y values
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
            if not isinstance( x_data_tuple,(frozenset, list, set, tuple,\
                                np.ndarray)):
                self.logMsg('Given range of axes is no array type.', \
                            msgType='error')  

            parameters=[amplitude,x_zero,y_zero,sigma_x,sigma_y,theta,offset]
            for var in parameters:
                if not isinstance(var,(float,int)):
                    self.logMsg('Given range of parameter' 
                                    'is no float or int.',msgType='error')
                                        
            (x, y) = x_data_tuple
            x_zero = float(x_zero)
            y_zero = float(y_zero) 
            
            a = (np.cos(theta)**2)/(2*sigma_x**2) \
                                        + (np.sin(theta)**2)/(2*sigma_y**2)
            b = -(np.sin(2*theta))/(4*sigma_x**2) \
                                        + (np.sin(2*theta))/(4*sigma_y**2)
            c = (np.sin(theta)**2)/(2*sigma_x**2) \
                                        + (np.cos(theta)**2)/(2*sigma_y**2)
            g = offset + amplitude*np.exp( - (a*((x-x_zero)**2) \
                                    + 2*b*(x-x_zero)*(y-y_zero) \
                                    + c*((y-y_zero)**2)))
            return g.ravel()
            
            
        def gaussian_function(self,x_data=None,amplitude=None, x_zero=None, sigma=None, offset=None):
            """ This method provides a one dimensional gaussian function.
        
            @param array x_data: x values
            @param float or int amplitude: Amplitude of gaussian
            @param float or int x_zero: x value of maximum
            @param float or int sigma: standard deviation
            @param float or int offset: offset

            @return callable function: returns a 1D Gaussian function
            
            """            
            # check if parameters make sense
            if not isinstance( x_data,(frozenset, list, set, tuple, np.ndarray)):
                self.logMsg('Given range of axis is no array type.', \
                            msgType='error') 


            parameters=[amplitude,x_zero,sigma,offset]
            for var in parameters:
                if not isinstance(var,(float,int)):
                    print('error',var)
                    self.logMsg('Given range of parameter is no float or int.', \
                                msgType='error')  
            gaussian = amplitude*np.exp(-(x_data-x_zero)**2/(2*sigma**2))+offset
            return gaussian 



##############################################################################
##############################################################################
##############################################################################

#                           old code


##############################################################################
##############################################################################
##############################################################################

                
#        def make_fit(self,function=None,axes=None,data=None,initial_guess=None,details=False):
#            """ Makes a fit of the desired function with the one and two 
#                dimensional data.
#        
#            @param callable function: The model function, f(x, ...).
#                    It must take the independent variable as the first argument
#                    and the parameters to fit as separate remaining arguments.
#            @param M-length sequence or an (k,M)-shaped array axes: Here the 
#                    axis or the axes are input. In one-dimensional case, simple
#                    array of x_axis; in two-dimensional case tuple of x_axis 
#                    and y_axis
#            @param M-length sequence data: The dependent data — nominally 
#                    f(xdata, ...)
#            @param None, scalar, or N-length sequence initial_guess: initial 
#                    guess with as many parameters as needed for the function
#            @param bool details: (optional) If set to False only the optimized 
#                    parameters will be returned. If set to True also the 
#                    estimated covariance is returned.
#        
#            @return int error: error code (0:OK, -1:error)
#            @return array popt: Optimal values for the parameters so that 
#                    the sum of the squared error of f(xdata, *popt) - ydata 
#                    is minimized
#            @return 2d array pcov: The estimated covariance of popt. The 
#                    diagonals provide the variance of the parameter estimate. 
#                    To compute one standard deviation errors on the parameters 
#                    use perr = np.sqrt(np.diag(pcov)).
#                    
#            """
#            # check if parameters make sense
#            error=0
#            popt=initial_guess
#            if initial_guess==None:
#                pcov=None
#            else:
#                pcov=np.zeros((len(initial_guess),len(initial_guess)))
#            
#            if not callable(function):
#                self.logMsg('Given "function" is no function.', \
#                            msgType='error')  
#                error =-1
#            if not isinstance( data,(frozenset, list, set, tuple, np.ndarray)):
#                self.logMsg('Given range of data is no array type.', \
#                            msgType='error')
#                error= -1
#            if not isinstance( axes,(frozenset, list, set, tuple, np.ndarray)):
#                self.logMsg('Given range of axes is no array type.', \
#                            msgType='error')
#                error= -1
#            if not isinstance(details,bool):
#                self.logMsg('Given bool details is not of type bool.', \
#                            msgType='error')
#                error= -1
#            if error==0:
#                try:
##                    FIXME: This is the actual fitting-function
#                    popt,pcov = opt.curve_fit(function,axes,data,initial_guess)
#                except:
#                    self.logMsg('The fit did not work.', msgType='warning')
#                    error=-1
#            if details==False:
#                return error,popt
#            elif details==True:
#                return error,popt, pcov
       


#        def make_twoD_gaussian_fit(self,x_axis=None,y_axis=None,data=None,details=False):
#            #FIXME: dimensions of arrays
#        
#            """ This method performes a 2D gaussian fit on the provided data.
#
#            @param array x_axis: x values
#            @param array y_axis: y values
#            @param array data: value of each data point corresponding to
#                                x and y values        
#            @param bool details: If details is True, additional to the fit 
#                                 parameters also the covariance matrix is
#                                 returned
#            
#                    
#            @return int error: error code (0:OK, -1:error)
#            @return array popt: Optimal values for the parameters so that 
#                    the sum of the squared error of f(xdata, *popt) - ydata 
#                    is minimized
#            @return 2d array pcov: The estimated covariance of popt. The 
#                    diagonals provide the variance of the parameter estimate. 
#                    To compute one standard deviation errors on the parameters 
#                    use perr = np.sqrt(np.diag(pcov)).
#                    
#            """
#                      
#            #FIXME: Would be nice in several rows....
#            error,amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset = self.twoD_gaussian_estimator(x_axis,y_axis,data)
#            initial_guess_estimated = (amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset)
#            
#            if details==False:
#                error,popt = self.make_fit(function=self.twoD_gaussian_function
#                                        ,axes=(x_axis,y_axis), data=data,
#                                        initial_guess=initial_guess_estimated)
#                return error,popt
#            elif details==True:
#                error,popt,pcov = self.make_fit(function=self.twoD_gaussian_function,axes=(x_axis,y_axis), 
#                                                data=data,initial_guess=initial_guess_estimated,
#                                                details=details)
#                return error,popt, pcov            

            

#        def lorentzian_function(self,x_data=None,amplitude=None, x_zero=None, sigma=None, offset=None):
#            """ This method provides a one dimensional Lorentzian function.
#        
#            @param array x_data: x values
#            @param float or int amplitude: Amplitude of Lorentzian
#            @param float or int x_zero: x value of maximum
#            @param float or int sigma: half width half maximum
#            @param float or int offset: offset
#
#            @return callable function: returns a 1D Lorentzian function
#            
#            """            
#            # check if parameters make sense
#            if not isinstance( x_data,(frozenset, list, set, tuple, np.ndarray)):
#                self.logMsg('Given range of axis is no array type.', \
#                            msgType='error') 
#
#
#            parameters=[amplitude,x_zero,sigma,offset]
#            for var in parameters:
#                if not isinstance(var,(float,int)):
#                    print('error',var)
#                    self.logMsg('Given range of parameter is no float or int.', \
#                                msgType='error') 
#                                
#            lorentzian = amplitude / np.pi * (  sigma / ( (x_data-x_zero)**2 + sigma**2 )  ) + offset
#            return lorentzian
#            
#           
#        def lorentzian_estimator(self,x_axis=None,data=None):
#            """ This method provides a one dimensional Lorentzian function.
#        
#            @param array x_axis: x values
#            @param array data: value of each data point corresponding to
#                                x values
#
#            @return int error: error code (0:OK, -1:error)
#            @return float amplitude: estimated amplitude
#            @return float x_zero: estimated x value of maximum
#            @return float sigma_x: estimated standard deviation in x direction
#            @return float offset: estimated offset
#                                
#                    
#            """
#            error=0
#            # check if parameters make sense
#            parameters=[x_axis,data]
#            for var in parameters:
#                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
#                    self.logMsg('Given parameter is no array.', \
#                                msgType='error') 
#                    error=-1
#                elif len(np.shape(var))!=1:
#                    self.logMsg('Given parameter is no one dimensional array.', \
#                                msgType='error')                     
#            #set paraameters 
#            offset=np.median(self.xdata)
#            #check if the amplitude is negative or positive and set x_zero:
#            data_norm=data-offset
#            if data_norm.max()>abs(data_norm.min()):
#                y_zero=data_norm.max()
#                x_zero=x_axis[np.argmax(data)]
#            else:
#                y_zero=data_norm.min()
#                x_zero=x_axis[np.argmin(data)]
#
#            #estimate amplitude and HWHM
#            Y = np.sum(data_norm) * (x_axis[-1] - x_axis[0]) / len(x_axis)
#            sigma = Y / (np.pi * y_zero)
#            amplitude = y_zero * np.pi * sigma
#
#            return error, amplitude, x_zero, sigma, offset     
# 
#
#        def make_lorentzian_fit(self,axis=None,data=None,details=False):
#            """ This method performes a gaussian fit on the provided data.
#        
#            @param array [] axis: axis values
#            @param array[]  x_data: data
#            @param bool details: If details is True, additional to the fit 
#                                 parameters also the covariance matrix is
#                                 returned
#            
#                    
#            @return int error: error code (0:OK, -1:error)
#            @return array popt: Optimal values for the parameters so that 
#                    the sum of the squared error of lorentzian_function(xdata,
#                    *popt)is minimized
#            @return 2d array pcov : The estimated covariance of popt. The 
#                    diagonals provide the variance of the parameter estimate. 
#                    To compute one standard deviation errors on the parameters 
#                    use perr = np.sqrt(np.diag(pcov)). This is only returned
#                    when details is set to true.
#                    
#            """
#                
#            error,amplitude, x_zero, sigma, offset = self.lorentzian_estimator(
#                                                                    axis,data)
#                                                                    
#            if details==False:
#                error,popt= self.make_fit(self.lorentzian_function, axis, 
#                                          data,initial_guess=(amplitude, 
#                                          x_zero, sigma, offset),
#                                          details=details)   
#                return error,popt
#            elif details==True:
#                error,popt,pcov= self.make_fit(self.lorentzian_function, axis, 
#                                               data,initial_guess=(amplitude, 
#                                               x_zero, sigma, offset),
#                                               details=details)
#                return error,popt, pcov

############################################################################################################               
############################################################################################################               
############################################################################################################               

###########################    New methods with lmfit libraray  ############################################

############################################################################################################               
############################################################################################################               
############################################################################################################               

        def substitute_parameter(self, parameters=None, update_parameters=None):
#TODO: Docstring
            
            for para in update_parameters:
                
                #store value because when max,min is set the value is overwritten
                # by the same number
                store_value=parameters[para].value
                value_is_new=(abs(update_parameters[para].value/store_value-1)<1e-20)
                
                #vary is set by default to True
                parameters[para].vary=update_parameters[para].vary 
                #check for other parameters and set in case
                

                if update_parameters[para].min!=None:
                    parameters[para].min=update_parameters[para].min  
                    
                if update_parameters[para].max!=None:
                    parameters[para].max=update_parameters[para].max   
                    
                if update_parameters[para].expr!=None:
                    parameters[para].expr=update_parameters[para].expr 
                
                parameters[para].value=store_value
                if value_is_new:
                    parameters[para].value=update_parameters[para].value 
                    
            return parameters

##############################################################################
##############################################################################

                        #1D gaussian model

##############################################################################
##############################################################################   
            
        def make_gaussian_model(self):
            """ This method creates a model of agaussian with an offset. The
            parameters are: 'amplitude', 'center', 'sigm, 'fwhm' and offset 
            'c'. For function see: 
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.GaussianModel
                            
            @return lmfit.model.CompositeModel model: Returns an object of the
                                                      class CompositeModel
            @return lmfit.parameter.Parameters params: Returns an object of the 
                                                       class Parameters with all
                                                       parameters for the 
                                                       gaussian model.
                    
            """
            
            model=GaussianModel()+ConstantModel()
            params=model.make_params()
            
            return model,params
            
        def make_gaussian_fit(self,axis=None,data=None, add_parameters=None):
            """ This method performes a 1D gaussian fit on the provided data.
        
            @param array [] axis: axis values
            @param array[]  x_data: data   
            @param dictionary add_parameters: Additional parameters
                    
            @return lmfit.model.ModelFit result: All parameters provided about 
                                                 the fitting, like: success,
                                                 initial fitting values, best 
                                                 fitting values, data with best
                                                 fit with given axis,...
                    
            """
                
            error,amplitude, x_zero, sigma, offset = self.estimate_gaussian(
                                                                    axis,data)
                                                                    
            mod_final,params = self.make_gaussian_model() 
            
            #auxiliary variables
            stepsize=axis[1]-axis[0]
            n_steps=len(axis)
            
            #Defining standard parameters
            #                  (Name,       Value,  Vary,         Min,                    Max,                    Expr)
            params.add_many(('amplitude',amplitude, True,         100,                    1e7,                    None),
                           (  'sigma',    sigma,    True,     1*(stepsize) ,              3*(axis[-1]-axis[0]),   None),
                           (  'center',  x_zero,    True,(axis[0])-n_steps*stepsize,(axis[-1])+n_steps*stepsize, None),
                           (    'c',      offset,   True,        None,                    None,                  None))

#TODO: Add logmessage when value is changed            
            #redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters)                                     
            try:
                result=mod_final.fit(data, x=axis,params=params)
            except:
                print("Fit did not work!")
            #                self.logMsg('The 1D gaussian fit did not work.', \
            #                            msgType='message')
                result=mod_final.fit(data, x=axis,params=params)
                print(result.message)
            
            return result

        def estimate_gaussian(self,x_axis=None,data=None):
            """ This method provides a one dimensional gaussian function.
        
            @param array x_axis: x values
            @param array data: value of each data point corresponding to
                                x values

            @return int error: error code (0:OK, -1:error)
            @return float amplitude: estimated amplitude
            @return float x_zero: estimated x value of maximum
            @return float sigma_x: estimated standard deviation in x direction
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
                    self.logMsg('Given parameter is no one dimensional array.', \
                                msgType='error')                     
            #set paraameters 
            x_zero=x_axis[np.argmax(data)]
            sigma = (x_axis.max()-x_axis.min())/3.            
            amplitude=(data.max()-data.min())*(sigma*np.sqrt(2*np.pi))
            offset=data.min()
            
            return error, amplitude, x_zero, sigma, offset
 

##############################################################################
##############################################################################

                        #2D gaussian model

##############################################################################
##############################################################################  

        def make_twoD_gaussian_fit(self,axis=None,data=None, add_parameters=None):
            """ This method performes a 1D gaussian fit on the provided data.
        
            @param array [] axis: axis values
            @param array[]  x_data: data   
            @param dictionary add_parameters: Additional parameters
                    
            @return lmfit.model.ModelFit result: All parameters provided about 
                                                 the fitting, like: success,
                                                 initial fitting values, best 
                                                 fitting values, data with best
                                                 fit with given axis,...
                    
            """
            (x_axis,y_axis)=axis
            error,amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset = self.twoD_gaussian_estimator(
                                                                            x_axis=x_axis,y_axis=y_axis,data=data)
            mod,params = self.make_twoD_gaussian_model() 
            #auxiliary variables
            stepsize_x=x_axis[1]-x_axis[0]
            stepsize_y=y_axis[1]-y_axis[0]
            n_steps_x=len(x_axis)
            n_steps_y=len(y_axis)
            
            #Defining standard parameters
            #                  (Name,       Value,      Vary,           Min,                             Max,                       Expr)
            params.add_many(('amplitude',   amplitude,  True,        100,                               1e7,                        None),
                           (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(x_axis[-1]-x_axis[0]),        None),
                           (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(y_axis[-1]-y_axis[0]) ,  None), 
                           (  'x_zero',    x_zero,      True,     (x_axis[0])-n_steps_x*stepsize_x ,         x_axis[-1]+n_steps_x*stepsize_x,               None),
                           (  'y_zero',     y_zero,     True,    (y_axis[0])-n_steps_y*stepsize_y ,         (y_axis[-1])+n_steps_y*stepsize_y,         None),
                           (  'theta',       0.,        True,           0. ,                             np.pi,               None),
                           (  'offset',      offset,    True,           0,                              1e7,                       None))
           
#TODO: Add logmessage when value is changed            
#            #redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters) 

            try:
                result=mod.fit(data, x=axis,params=params)
            except:
                print("Fit did not work!")
            #                self.logMsg('The 1D gaussian fit did not work.', \
            #                            msgType='message')
            
            return result
            
        @staticmethod
        def twoD_gaussian_model(x,amplitude,x_zero,y_zero,sigma_x,sigma_y,theta, offset):
                                        
            #FIXME: x_data_tuple: dimension of arrays
                                    
            """ This method provides a two dimensional gaussian function.
            
            @param (k,M)-shaped array x_data_tuple: x and y values
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
                self.logMsg('Given range of axes is no array type.', \
                            msgType='error') 

            parameters=[amplitude,x_zero,y_zero,sigma_x,sigma_y,theta,offset]
            for var in parameters:
                if not isinstance(var,(float,int)):
                    self.logMsg('Given range of parameter' 
                                    'is no float or int.',msgType='error')
                                           
            (u,v)=x
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
            """ This method creates a model of the 2D gaussian function. The
            parameters are: 'amplitude', 'center', 'sigm, 'fwhm' and offset 
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
            
        def twoD_gaussian_estimator(self,x_axis=None,y_axis=None,data=None):
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