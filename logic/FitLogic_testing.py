# -*- coding: utf-8 -*-

import numpy as np
import scipy.optimize as opt
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel
from lmfit import Parameters
import scipy
import pylab as plt

#for filters:
from scipy.interpolate import UnivariateSpline
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import scipy.optimize as op

#TODO:
#Make Estimator, Fit method, comments, try smooth as estimator
class FitLogic():        
        """
        UNSTABLE:Jochen Scheuer
        This is the fitting class where  fit functions are defined and methods
        are implemented to process the data.
        
        """
        
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
            """ This method substitutes all parameters handed in the 
            update_parameters object in an initial set of parameters.
                            
            @param lmfit.parameter.Parameters parameters: Initial parameters
            @param lmfit.parameter.Parameters update_parameters: New parameters
            
            @return lmfit.parameter.Parameters parameters: New object with
                                                           substituted parameters
                    
            """
            
            for para in update_parameters:
                #store value because when max,min is set the value is overwritten
                store_value=parameters[para].value
                
                #the Parameter object changes the value, min and max when the 
#                value is called therefore the parameters have to be saved from 
#                the reseted Parameter object therefore the Parameters have to be
#                saved also here
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
                    
                #vary is set by default to True
                parameters[para].vary=update_parameters[para].vary 

#                if the min, max and expression and value are new overwrite them here                    
                if min_new:
                    parameters[para].min=update_parameters[para].min
                    
                if max_new:
                    parameters[para].max=update_parameters[para].max   
                
                if update_parameters[para].expr!=None:
                    parameters[para].expr=update_parameters[para].expr
                
                if value_new:
                    parameters[para].value=value_value
                    
#                if the min or max are changed they overwrite the value therefore
#                    here the values have to be reseted to the initial value also
#                    when no new value was set in the beginning
                if min_new:
                    if abs(min_value/parameters[para].value-1.)<1e-12:
                        parameters[para].value=store_value                        
                if max_new:
                    if abs(max_value/parameters[para].value-1.)<1e-12:
                        parameters[para].value=store_value

                #check if the suggested value or the value in parameters is smaller/
#                bigger than min/max values and set then the value to min or max                        
                if min_new:
                    if parameters[para].value<min_value:
                        parameters[para].value=min_value 

                if max_new:
                    if parameters[para].value>max_value:
                        parameters[para].value=max_value 
                    
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

            #When I was sitting in the train coding and my girlfiend was sitting next to me she said: "Look it looks like an animal!" - is it a fox or a rabbit???
            
            #Defining standard parameters
            #                  (Name,       Value,      Vary,           Min,                             Max,                       Expr)
            params.add_many(('amplitude',   amplitude,  True,        100,                               1e7,                           None),
                           (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(x_axis[-1]-x_axis[0]),           None),
                           (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(y_axis[-1]-y_axis[0]) ,    None), 
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


 

##############################################################################
##############################################################################

                        #Lorentzian Model

##############################################################################
##############################################################################  

        def make_lorentzian_model(self):
            """ This method creates a model of lorentzian with an offset. The
            parameters are: 'amplitude', 'center', 'sigma, 'fwhm' and offset 
            'c'. For function see: 
            http://cars9.uchicago.edu/software/python/lmfit/builtin_models.html#models.LorentzianModel                            

            @return lmfit.model.CompositeModel model: Returns an object of the
                                                      class CompositeModel
            @return lmfit.parameter.Parameters params: Returns an object of the 
                                                       class Parameters with all
                                                       parameters for the 
                                                       lorentzian model.
                    
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
                    self.logMsg('Given parameter is no array.', \
                                msgType='error') 
                    error=-1
                elif len(np.shape(var))!=1:
                    self.logMsg('Given parameter is no one dimensional array.', \
                                msgType='error')                     
            #set paraameters 
                                
#           gaussian filter            
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data, gaus/gaus.sum())
            offset=data_smooth.max()

            data_level=data-offset        
            data_min=data_level.min()       
            data_max=data_level.max()

            #estimate sigma
            numerical_integral=np.sum(data_level) * (x_axis[-1] - x_axis[0]) / len(x_axis)

            sigma = (x_axis.max()-x_axis.min())/3.

            if data_max>abs(data_min):
                try:
                    self.logMsg('The lorentzian estimator set the peak to the minimal value, if you want to fit a peak instead of a dip rewrite the estimator.', \
                                    msgType='warning')     
                except:
                    print('The lorentzian estimator set the peak to the minimal value, if you want to fit a peak instead of a dip rewrite the estimator.')

            amplitude_median=data_min
            x_zero=x_axis[np.argmin(data_smooth)]

            sigma = numerical_integral / (np.pi * amplitude_median)            
            amplitude=amplitude_median * np.pi * sigma
            
            return error, amplitude, x_zero, sigma, offset

        def make_lorentzian_fit(self,axis=None,data=None, add_parameters=None):
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
                
            error,amplitude, x_zero, sigma, offset = self.estimate_lorentz(
                                                                    axis,data)
                                                                    
            model,params = self.make_lorentzian_model() 
            
            #auxiliary variables
            stepsize=axis[1]-axis[0]
            n_steps=len(axis)

#            TODO: Make sigma amplitude and x_zero better            
            #Defining standard parameters
            #                  (Name,       Value,  Vary,         Min,                    Max,                    Expr)
            params.add_many(('amplitude',amplitude, True,         None,                    -1e-12,                    None),
                           (  'sigma',    sigma,    True,     (axis[1]-axis[0])/2 ,     (axis[-1]-axis[0])*10,   None),
                           (  'center',  x_zero,    True,(axis[0])-n_steps*stepsize,(axis[-1])+n_steps*stepsize, None),
                           (    'c',      offset,   True,        None,                    None,                  None))

            print('offset in m',offset)
#TODO: Add logmessage when value is changed            
            #redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters)                                     
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                print("Fit did not work!")
            #                self.logMsg('The 1D gaussian fit did not work.', \
            #                            msgType='message')
                result=model.fit(data, x=axis,params=params)
                print(result.message)
            
            return result

##############################################################################
##############################################################################

                        #Double Lorentzian Model

##############################################################################
##############################################################################  

            
        def make_multiple_lorentzian_model(self,no_of_lor=None):
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
            
            return model,params
     
            
        def estimate_double_lorentz(self,x_axis=None,data=None):
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
                    self.logMsg('Given parameter is no array.', \
                                msgType='error') 
                    error=-1
                elif len(np.shape(var))!=1:
                    self.logMsg('Given parameter is no one dimensional array.', \
                                msgType='error')
                                
            
            #set paraameters 
            
            #gaussian filter            
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data, gaus/gaus.sum())
            
            #finding most frequent value which is supposed to be the offset
            hist=np.histogram(data_smooth,bins=10)
            offset=(hist[1][hist[0].argmax()]+hist[1][hist[0].argmax()+1])/2.
            
            data_level=data-offset        

            #minima search
            mid_index=int(len(x_axis)/2)
            
            absolute_min=data_level.min()
            
            #TODO: make treshold and deadzone value a config variable
            treshold=0.4*absolute_min
            minimal_treshold=0.001
            deadzone=int(4)
            
            left_index=int(0)
            right_index=len(x_axis)-1
            
            while True:                
                left_min=data_level[left_index:mid_index-deadzone+1].min()
                left_argmin=data_level[left_index:mid_index-deadzone+1].argmin()
                right_min=data_level[mid_index:right_index].min()
                right_argmin=data_level[mid_index:right_index].argmin()
                
                if abs(right_min)>abs(treshold) and abs(left_min)>abs(treshold):
                    #found two minima successfully
                    lorentz0_amplitude=left_min
                    lorentz0_center=x_axis[left_argmin+left_index]
                    lorentz1_amplitude=right_min
                    lorentz1_center=x_axis[right_argmin+mid_index]
                    break
                elif abs(left_min)>abs(treshold):
                    #there is no minimum exceeding treshold so shift area to search
                    right_index=mid_index
                    mid_index=int((right_index+left_index)/2.-1)
                elif abs(right_min)>abs(treshold):
                    #there is no minimum exceeding treshold so shift area to search
                    left_index=mid_index
                    mid_index=int((right_index+left_index)/2.-1)
                else: 
                    #no minimum at all over treshold so lowering treshold and resetting search area
                    treshold=treshold*2./3.
                    left_index=int(0)
                    right_index=len(x_axis)-1
                    mid_index=int(len(x_axis)/2)        
                    if (treshold/absolute_min)<minimal_treshold:
                        self.logMsg('Treshold to minimum ratio was too small to estimate two minima.', \
                                msgType='message') 
                        lorentz0_center=x_axis[data.argmin()]   
                        lorentz1_center=lorentz0_center
                        break
                    print('treshold')
                    
                if abs(mid_index-left_index)<deadzone or abs(right_index-mid_index)<deadzone:
                    #peaks are too close, probably there is only one
                    if abs(left_min)<abs(right_min):
                        print('here 1')
                        left_argmin=right_argmin
                        lorentz0_amplitude=right_min/2.
                        lorentz0_center=x_axis[right_argmin+mid_index]                     
                    else:
                        right_argmin=left_argmin
                        lorentz0_amplitude=left_min/2.
                        lorentz0_center=x_axis[left_argmin+left_index] 
                        print('here')
                    lorentz1_amplitude=lorentz0_amplitude/2.
                    lorentz1_center=lorentz0_center
                    break
            
            #estimate sigma
            numerical_integral=np.sum(data_level) * (x_axis[-1] - x_axis[0]) / len(x_axis)

            lorentz0_sigma = abs(numerical_integral / (np.pi * lorentz0_amplitude) )  
            lorentz1_sigma = abs( numerical_integral / (np.pi * lorentz1_amplitude)  )

            #esstimate amplitude
            lorentz0_amplitude=-1*abs(lorentz0_amplitude*np.pi*lorentz0_sigma)
            lorentz1_amplitude=-1*abs(lorentz1_amplitude*np.pi*lorentz1_sigma)

            return error, lorentz0_amplitude,lorentz1_amplitude, lorentz0_center,lorentz1_center, lorentz0_sigma,lorentz1_sigma, offset

        def make_double_lorentzian_fit(self,axis=None,data=None,add_parameters=None):
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
                
            error, lorentz0_amplitude,lorentz1_amplitude, lorentz0_center,lorentz1_center, lorentz0_sigma,lorentz1_sigma, offset = self.estimate_double_lorentz(axis,data)
                                                                    
            model,params = self.make_multiple_lorentzian_model(no_of_lor=2)
            
            #auxiliary variables
            stepsize=axis[1]-axis[0]
            n_steps=len(axis)
#            TODO: Make sigma amplitude and x_zero better            
            #Defining standard parameters
            #            (Name,                  Value,          Vary,         Min,                    Max,                    Expr)
            params.add('lorentz0_amplitude',lorentz0_amplitude,  True,         None,                    -0.01,                    None)
            params.add(  'lorentz0_sigma',    lorentz0_sigma,    True,    (axis[1]-axis[0])/2 ,     (axis[-1]-axis[0])*4,   None)
            params.add(  'lorentz0_center',  lorentz0_center,    True,(axis[0])-n_steps*stepsize,(axis[-1])+n_steps*stepsize, None)
            params.add('lorentz1_amplitude',lorentz1_amplitude,  True,         None,                    -0.01,                    None)
            params.add(  'lorentz1_sigma',    lorentz1_sigma,    True,     (axis[1]-axis[0])/2 ,     (axis[-1]-axis[0])*4,   None)
            params.add(  'lorentz1_center',  lorentz1_center,    True,(axis[0])-n_steps*stepsize,(axis[-1])+n_steps*stepsize, None)
            params.add(    'c',                   offset,        True,        None,                    None,                  None)

#            print(params)

#           TODO: Add logmessage when value is changed            
            #redefine values of additional parameters
#            if add_parameters!=None:  
#                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters)                                     
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                print("Fit did not work!")
            #                self.logMsg('The 1D gaussian fit did not work.', \
            #                            msgType='message')
                result=model.fit(data, x=axis,params=params)
                print(result.message)
            
            return result

            
##############################################################################
##############################################################################

                        #Testing routines

##############################################################################
##############################################################################  
         

            
        def double_lorentzian_testing(self):
            x = np.linspace(2800, 2900, 101)
            
            mod,params = self.make_multiple_lorentzian_model(no_of_lor=2)
#            print('Parameters of the model',mod.param_names)
            
            p=Parameters()
            
#            p.add('center',max=-1)
            p.add('lorentz0_amplitude',value=-abs(np.random.normal(15,5)))
            p.add('lorentz0_center',value=np.random.normal(2840,15))
            p.add('lorentz0_sigma',value=abs(np.random.normal(3,2)))
            p.add('lorentz1_amplitude',value=-abs(np.random.normal(15,5)))
            p.add('lorentz1_center',value=np.random.normal(2860,15))
            p.add('lorentz1_sigma',value=abs(np.random.normal(3,1)))
            p.add('c',value=100.)
            
            print('center left, right',p['lorentz0_center'].value,p['lorentz1_center'].value)
            data_noisy=(mod.eval(x=x,params=p) 
                                    + 0.3*np.random.normal(size=x.shape))
                                    
            para=Parameters()
#            para.add('sigma',min=0.1)

            result=self.make_double_lorentzian_fit(axis=x,data=data_noisy,add_parameters=para)
            print('center 1 und 2',result.init_values['lorentz0_center'],result.init_values['lorentz1_center'])
            
            print('center 1 und 2',result.best_values['lorentz0_center'],result.best_values['lorentz1_center'])
            #           gaussian filter            
            gaus=gaussian(10,10)
            data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum())
                   

            try:
#            print(result.fit_report()
                plt.plot(x,result.init_fit,'-g')
                plt.plot(x,result.best_fit,'-r')
                plt.plot(x,data_smooth,'-y')
            except:
                print('exception')
##            plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'-r')#
            plt.plot(x,data_noisy)
            plt.show()
            
        def lorentzian_testing(self):
            x = np.linspace(900, 1000, 31)
            
            mod,params = self.make_lorentzian_model()
            print('Parameters of the model',mod.param_names)
            p=Parameters()
            
#            p.add('center',max=-1)
            p.add('amplitude',value=-100.)
            p.add('center',value=920.)
            p.add('sigma',value=10)
            p.add('c',value=10.)
            
            data_noisy=(mod.eval(x=x,params=p)
                                    + 0.2*np.random.normal(size=x.shape))
                                    
            para=Parameters()
            para.add('sigma',value=p['sigma'].value)
            para.add('amplitude',value=p['amplitude'].value)

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
            
#            p.add('center',max=-1)
            
            self.data_noisy=mod_final.eval(x=self.x, amplitude=100000,center=1,sigma=0.8, c=10000) + 10000*np.random.normal(size=self.x.shape)
            result=self.make_gaussian_fit(axis=self.x,data=self.data_noisy,add_parameters=p)

            plt.plot(self.x,self.data_noisy)
            plt.plot(self.x,result.init_fit,'-g')
            plt.plot(self.x,result.best_fit,'-r')
#            plt.plot(x_nice,mod_final.eval(x=x_nice,params=result.params),'-r')
            plt.show()
            
            
#nice things from this class
#            print('success',result.success)
#            print('center',result.params['center'].value)
            
test=FitLogic()
test.double_lorentzian_testing()   