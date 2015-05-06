# -*- coding: utf-8 -*-

import numpy as np
import scipy.optimize as opt#, scipy.stats
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
                    popt,pcov = opt.curve_fit(function,axes,data,initial_guess)
                except:
                    self.logMsg('The fit did not work.', msgType='error')
                    error=-1
            if details==False:
                return error,popt
            elif details==True:
                return error,popt, pcov
        
        def twoD_gaussian_function(self,x_data_tuple=None,amplitude=None,\
                                    x_zero=None, y_zero=None, sigma_x=None, \
                                    sigma_y=None, theta=None, offset=None):
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
            
        def twoD_gaussian_estimator(self,x_axis=None,y_axis=None,data=None):
#            TODO:Make clever estimator
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


        def make_twoD_gaussian_fit(self,x_axis=None,y_axis=None,data=None,details=False):
            """ This method performes a 2D gaussian fit on the provided data.

            @param array x_axis: x values
            @param array y_axis: y values
            @param array data: value of each data point corresponding to
                                x and y values        
            @param bool details: If details is True, additional to the fit 
                                 parameters also the covariance matrix is
                                 returned
            
                    
            @return int error: error code (0:OK, -1:error)
            @return array popt: Optimal values for the parameters so that 
                    the sum of the squared error of f(xdata, *popt) - ydata 
                    is minimized
            @return 2d array pcov: The estimated covariance of popt. The 
                    diagonals provide the variance of the parameter estimate. 
                    To compute one standard deviation errors on the parameters 
                    use perr = np.sqrt(np.diag(pcov)).
                    
            """
            details_here=details
            error=0
                
            error,amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset = self.twoD_gaussian_estimator(x_axis,y_axis,data)
            initial_guess_estimated = (amplitude, x_zero, y_zero, sigma_x, sigma_y, theta, offset)
            
            if details==False:
                error,popt = self.make_fit(function=self.twoD_gaussian_function,axes=(x_axis,y_axis), data=data,initial_guess=initial_guess_estimated)
                return error,popt
            elif details==True:
                error,popt,pcov = self.make_fit(function=self.twoD_gaussian_function,axes=(x_axis,y_axis), data=data,initial_guess=initial_guess_estimated,details=details_here)
                return error,popt, pcov            
            
        def gaussian_function(self,x_data=None,amplitude=None, x_zero=None, sigma=None, offset=None):
            """ This method provides a two dimensional gaussian function.
        
            @param array x_data: x values
            @param float or int amplitude: Amplitude of gaussian
            @param float or int x_zero: x value of maximum
            @param float or int sigma: standard deviation
            @param float or int offset: offset

            @return callable function: returns the function
                    
            """
            # check if parameters make sense
            if not isinstance( x_data,(frozenset, list, set, tuple, np.ndarray)):
                print("error")
                self.logMsg('Given range of axes is no array type.', \
                            msgType='error')            

            parameters=[amplitude,x_zero,sigma,offset]
            for var in parameters:
                if not isinstance(var,(float,int)):
                    print('error',var)
                    self.logMsg('Given range of parameter is no float or int.', \
                                msgType='error')  
            gaussian = amplitude*np.exp(-(x_data-x_zero)**2/(2*sigma**2))+offset
            return gaussian
        
        def gaussian_estimator(self,x_axis=None,data=None):
#            TODO:Make clever estimator
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
            error=0
            # check if parameters make sense
            parameters=[x_axis,data]
            for var in parameters:
                if not isinstance(var,(frozenset, list, set, tuple, np.ndarray)):
                    self.logMsg('Given parameter is no array.', \
                                msgType='error') 
                    error=-1
            #set paraameters        
            amplitude=data.max()
            x_zero = x_axis.min() + (x_axis.max()-x_axis.min())/3.
            sigma=(x_axis.max()-x_axis.min())/2.
            offset=data.min()
            return error, amplitude, x_zero, sigma, offset

        def make_gaussian_fit(self,axis=None,data=None,details=False):
            """ This method performes a gaussian fit on the provided data.
        
            @param array axis: axis values
            @param array x_data: data
            @param bool details: If details is True, additional to the fit 
                                 parameters also the covariance matrix is
                                 returned
            
                    
            @return int error: error code (0:OK, -1:error)
            @return array popt: Optimal values for the parameters so that 
                    the sum of the squared error of f(xdata, *popt) - ydata 
                    is minimized
            @return 2d array pcov: The estimated covariance of popt. The 
                    diagonals provide the variance of the parameter estimate. 
                    To compute one standard deviation errors on the parameters 
                    use perr = np.sqrt(np.diag(pcov)).
                    
            """
            details_here=details
            error=0
                
            error,amplitude, x_zero, sigma, offset = self.gaussian_estimator(
                                                                    axis,data)
            
            if details==False:
                error,popt= self.make_fit(self.gaussian_function, axis, 
                                          data,initial_guess=(amplitude, 
                                          x_zero, sigma, offset),
                                          details=details_here)   
                return error,popt
            elif details==True:
                error,popt,pcov= self.make_fit(self.gaussian_function, axis, 
                                               data,initial_guess=(amplitude, 
                                               x_zero, sigma, offset),
                                               details=details_here)
                return error,popt, pcov
                
        def oneD_testing(self):
            self.x = np.linspace(0, 200, 201)
            self.xdata=self.gaussian_function(self.x,30,101,70,5)
            self.xdata_noisy=self.xdata\
                                    +2*np.random.normal(size=self.xdata.shape)
            error,popt=self.make_gaussian_fit(self.x,self.xdata_noisy)
            plt.figure()
            plt.plot(self.x,self.gaussian_function(self.x, *popt))
            plt.plot(self.xdata_noisy)
            plt.show()
            

        
        def twoD_testing(self):    
            # Create x and y indices
            self.x = np.linspace(0, 200, 201)
            self.y = np.linspace(0, 200, 201)
            self.x, self.y = np.meshgrid(self.x, self.y)
            
            #create data
            data = self.twoD_gaussian_function((self.x, self.y), 3, 
                                               100, 100, 20, 40, 10, 10)
            
            # add some noise to the data and try to fit the data generated beforehand
            
            self.data_noisy = data + 0.2*np.random.normal(size=data.shape)
            error,popt = self.make_twoD_gaussian_fit(self.x,self.y
                                                    ,self.data_noisy)
            data_fitted = self.twoD_gaussian_function((self.x, self.y), *popt)
            fig, ax = plt.subplots(1, 1)
            ax.hold(True)
            ax.imshow(self.data_noisy.reshape(201, 201), cmap=plt.cm.jet, 
                      origin='bottom', extent=(self.x.min(), self.x.max(), 
                                               self.y.min(), self.y.max()))
            ax.contour(self.x, self.y, data_fitted.reshape(201, 201), 8
                        , colors='w')


test=FitLogic()
test.twoD_testing()   