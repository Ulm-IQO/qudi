# -*- coding: utf-8 -*-

import numpy as np
import scipy.optimize as opt
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel
from lmfit import Parameters

import pylab as plt

#TODO:
#Make Estimator, Fit method, comments, try smooth as estimator
class FitLogic():        
        """
        UNSTABLE:Jochen Scheuer
        This is the fitting class where  fit functions are defined and methods
        are implemented to process the data.
        
        """
        
        def make_fit(self,function=None,axes=None,data=None,initial_guess=None,details=False):
            """ Makes a fit of the desired function with the one and two 
                dimensional data.
        
            @param callable function: The model function, f(x, ...).
                    It must take the independent variable as the first argument
                    and the parameters to fit as separate remaining arguments.
            @param M-length sequence or an (k,M)-shaped array axes: Here the 
                    axis or the axes are input. In one-dimensional case, simple
                    array of x_axis; in two-dimensional case tuple of x_axis 
                    and y_axis
            @param M-length sequence data: The dependent data — nominally 
                    f(xdata, ...)
            @param None, scalar, or N-length sequence initial_guess: initial 
                    guess with as many parameters as needed for the function
            @param bool details: (optional) If set to False only the optimized 
                    parameters will be returned. If set to True also the 
                    estimated covariance is returned.
        
            @return int error: error code (0:OK, -1:error)
            @return array popt: Optimal values for the parameters so that 
                    the sum of the squared error of f(xdata, *popt) - ydata 
                    is minimized
            @return 2d array pcov: The estimated covariance of popt. The 
                    diagonals provide the variance of the parameter estimate. 
                    To compute one standard deviation errors on the parameters 
                    use perr = np.sqrt(np.diag(pcov)).
                    
            """
            # check if parameters make sense
            error=0
            popt=initial_guess
            if initial_guess==None:
                pcov=None
            else:
                pcov=np.zeros((len(initial_guess),len(initial_guess)))
            
            if not callable(function):
                self.logMsg('Given "function" is no function.', \
                            msgType='error')  
                error =-1
            if not isinstance( data,(frozenset, list, set, tuple, np.ndarray)):
                self.logMsg('Given range of data is no array type.', \
                            msgType='error')
                error= -1
            if not isinstance( axes,(frozenset, list, set, tuple, np.ndarray)):
                self.logMsg('Given range of axes is no array type.', \
                            msgType='error')
                error= -1
            if not isinstance(details,bool):
                self.logMsg('Given bool details is not of type bool.', \
                            msgType='error')
                error= -1
            if error==0:
                try:
#                    FIXME: This is the actual fitting-function
                    popt,pcov = opt.curve_fit(function,axes,data,initial_guess)
                except:
                    self.logMsg('The fit did not work.', msgType='warning')
                    error=-1
            if details==False:
                return error,popt
            elif details==True:
                return error,popt, pcov
        
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
            

        def lorentzian_function(self,x_data=None,amplitude=None, x_zero=None, sigma=None, offset=None):
            """ This method provides a one dimensional Lorentzian function.
        
            @param array x_data: x values
            @param float or int amplitude: Amplitude of Lorentzian
            @param float or int x_zero: x value of maximum
            @param float or int sigma: half width half maximum
            @param float or int offset: offset

            @return callable function: returns a 1D Lorentzian function
            
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
                                
            lorentzian = amplitude / np.pi * (  sigma / ( (x_data-x_zero)**2 + sigma**2 )  ) + offset
            return lorentzian
            
           
        def lorentzian_estimator(self,x_axis=None,data=None):
            """ This method provides a one dimensional Lorentzian function.
        
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
            offset=np.median(self.xdata)
            #check if the amplitude is negative or positive and set x_zero:
            data_norm=data-offset
            if data_norm.max()>abs(data_norm.min()):
                y_zero=data_norm.max()
                x_zero=x_axis[np.argmax(data)]
            else:
                y_zero=data_norm.min()
                x_zero=x_axis[np.argmin(data)]

            #estimate amplitude and HWHM
            Y = np.sum(data_norm) * (x_axis[-1] - x_axis[0]) / len(x_axis)
            sigma = Y / (np.pi * y_zero)
            amplitude = y_zero * np.pi * sigma

            return error, amplitude, x_zero, sigma, offset     
 

        def make_lorentzian_fit(self,axis=None,data=None,details=False):
            """ This method performes a gaussian fit on the provided data.
        
            @param array [] axis: axis values
            @param array[]  x_data: data
            @param bool details: If details is True, additional to the fit 
                                 parameters also the covariance matrix is
                                 returned
            
                    
            @return int error: error code (0:OK, -1:error)
            @return array popt: Optimal values for the parameters so that 
                    the sum of the squared error of lorentzian_function(xdata,
                    *popt)is minimized
            @return 2d array pcov : The estimated covariance of popt. The 
                    diagonals provide the variance of the parameter estimate. 
                    To compute one standard deviation errors on the parameters 
                    use perr = np.sqrt(np.diag(pcov)). This is only returned
                    when details is set to true.
                    
            """
                
            error,amplitude, x_zero, sigma, offset = self.lorentzian_estimator(
                                                                    axis,data)
                                                                    
            if details==False:
                error,popt= self.make_fit(self.lorentzian_function, axis, 
                                          data,initial_guess=(amplitude, 
                                          x_zero, sigma, offset),
                                          details=details)   
                return error,popt
            elif details==True:
                error,popt,pcov= self.make_fit(self.lorentzian_function, axis, 
                                               data,initial_guess=(amplitude, 
                                               x_zero, sigma, offset),
                                               details=details)
                return error,popt, pcov

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
                #vary is set by default to True
                parameters[para].vary=update_parameters[para].vary 
                #check for other parameters and set in case
                
                #store value because when max,min is set the value is overwritten
                # by the same number
                store_value=parameters[para].value
                if update_parameters[para].min!=None:
                    parameters[para].min=update_parameters[para].min  
                    
                if update_parameters[para].max!=None:
                    parameters[para].max=update_parameters[para].max   
                    
                if update_parameters[para].expr!=None:
                    parameters[para].expr=update_parameters[para].expr 
                
                parameters[para].value=store_value
                if update_parameters[para].value!=None:
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
            error,amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset = self.twoD_gaussian_estimator(
                                                                            x_axis=axis[:,0],y_axis=axis[:,0],data=data)
            mod,params = self.make_twoD_gaussian_model() 
             
            #auxiliary variables
            stepsize_x=axis[1,0]-axis[0,0]
            stepsize_y=axis[1,1]-axis[0,1]
            n_steps_x=len(axis[:,0])
            n_steps_y=len(axis[:,1])
            
            #Defining standard parameters
            #                  (Name,       Value,      Vary,           Min,                             Max,                       Expr)
            params.add_many(('amplitude',   amplitude,  True,        100,                               1e7,                        None),
                           (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(axis[-1,0]-axis[0,0]),        None),
                           (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(axis[-1,0]-axis[0,0]) ,  None), 
                           (  'x_zero',    x_zero,      True,     (axis[0,0])-n_steps_x*stepsize_x ,         (axis[-1,0])+n_steps_x*stepsize_x,               None),
                           (  'y_zero',     y_zero,     True,    (axis[0,1])-n_steps_y*stepsize_y ,         (axis[-1,1])+n_steps_y*stepsize_y,         None),
                           (  'theta',    0,        True,           0 ,                             np.pi,               None),
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
                                        
            u = x[:, 0]
            v = x[:, 1]                            
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
            #FIXME: Idea: x_zero@max x_axis
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
            amplitude=float(data.max()-data.min())
            x_zero = x_axis.min() + (x_axis.max()-x_axis.min())/2.  
            y_zero = y_axis.min() + (y_axis.max()-y_axis.min())/2.  
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


        def twoD_testing(self):
            data = np.empty((2500,1))
            x = np.arange(-2,3,0.1)
            y = np.arange(-2,3,0.1)
            xx, yy = np.meshgrid(x, y)
            
            axes = np.empty((len(data),2))
            axes[:,0]=xx.flatten()
            axes[:,1]=yy.flatten()           
            theta_here=110./360.*(2*np.pi)
            data= self.twoD_gaussian_model(x=axes,amplitude=100000,x_zero=0.9,y_zero=0.5,sigma_x=2,sigma_y=1,theta=theta_here, offset=10000)
            gmod,params = self.make_twoD_gaussian_model()
            
            para=Parameters()
#            para.add('sigma_x',expr='0.5*sigma_y')
            para.add('amplitude',min=20000)
            result=self.make_twoD_gaussian_fit(axis=axes,data=data,add_parameters=para)
            fig, ax = plt.subplots(1, 1)
            ax.hold(True)
            ax.imshow(gmod.eval(x=axes,amplitude=100000,x_zero=0.9,y_zero=0.5,sigma_x=2,sigma_y=1,theta=theta_here, offset=10000).reshape(50, 50), cmap=plt.cm.jet, 
                      origin='bottom', extent=(x.min(), x.max(), 
                                               y.min(), y.max()))
            ax.contour(x, y, result.best_fit.reshape(50, 50), 8
                        , colors='w')
                                    
                                    

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
test.oneD_testing()   