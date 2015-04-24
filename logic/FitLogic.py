# -*- coding: utf-8 -*-
from logic.GenericLogic import GenericLogic
from pyqtgraph.Qt import QtCore
from core.util.Mutex import Mutex
from collections import OrderedDict

import numpy as np
import scipy.optimize as opt#, scipy.stats
import pylab as plt

#TODO:
#Make Estimator, Fit method, comments, try smooth as estimator
class FitLogic(GenericLogic):        
        """
        UNSTABLE:Jochen Scheuer
        This is the fitting class where  fit functions are defined and methods
        are implemented to process the data.
        
        """
        
        def __init__(self, manager, name, config, **kwargs):
            ## declare actions for state transitions
            state_actions = {'onactivate': self.activation}
            GenericLogic.__init__(self, manager, name, config, state_actions, **kwargs)
            self._modclass = 'counterlogic'
            self._modtype = 'logic'
    
            ## declare connectors
            
            self.connector['out']['fitlogic'] = OrderedDict()
            self.connector['out']['fitlogic']['class'] = 'FitLogic'
            
            #locking for thread safety
            self.lock = Mutex()
    
            self.logMsg('The following configuration was found.', 
                        msgType='status')
                                
#            # checking for the right configuration
#            for key in config.keys():
#                self.logMsg('{}: {}'.format(key,config[key]), 
#                            msgType='status')
                             
        def activation(self,e):
            self.oneD_testing()
            self.twoD_testing()
            
        def make_fit(self,function=None,axes=None,data=None,initial_guess=None,details=False):
            """ Makes a fit of the desired function with the one and two dimensional data.
        
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
            @param int details: (optional) If set to None only the optimized 
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
            if not isinstance( data, (frozenset, list, set, tuple, np.ndarray, ) ):
                self.logMsg('Given range of data is no array type.', \
                            msgType='error')
                error= -1
            if not isinstance( axes, (frozenset, list, set, tuple, np.ndarray, ) ):
                self.logMsg('Given range of axes is no array type.', \
                            msgType='error')
                error= -1
            if error==0:
                try:
                    popt, pcov = opt.curve_fit(function,axes,data,initial_guess)
                except:
                    self.logMsg('The fit did not work.', 
                        msgType='status')
                    error=-1
                
            if not details:
                return error,popt
            else:    
                return error,popt, pcov
        
        def twoD_gaussian_function(self,xdata_tuple,amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
            (x, y) = xdata_tuple
            # not xo but rather x_zero
            xo = float(xo)
            yo = float(yo)    
            a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)
            b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)
            c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)
            g = offset + amplitude*np.exp( - (a*((x-xo)**2) + 2*b*(x-xo)*(y-yo) 
                                    + c*((y-yo)**2)))
            return g.ravel()
            
        def twoD_gaussian_estimator(self,dimension_x=None,dimenstion_y=None,data=None):
#            TODO:Make clever estimator
            #get some initial values
            amplitude=data.max()-data.min()
            # not xo but rather x_zero
            xo=len(dimension_x)/2.
            yo=len(dimenstion_y)/2.
            sigma_x=xo/3
            sigma_y =yo/3
            theta=0
            offset=data.min()
            return amplitude, xo, yo, sigma_x, sigma_y, theta, offset
            
            
        def gaussian_function(self,xdata=None,amplitude=None, x0=None, sigma=None):
            # offset
            gaussian=amplitude*np.exp(-(xdata-x0)**2/(2*sigma**2))
            return gaussian
        
        def gaussian_estimator(self,axis_x,data):
#            TODO:Make clever estimator
            amplitude=data.max()
            # consistent parameter names
            x0=len(axis_x)/2.
            sigma=x0/3
            return amplitude, x0, sigma
        
        def oneD_testing(self):
            self.x = np.linspace(0, 200, 201)
            
            self.xdata=self.gaussian_function(self.x,10,80,20)
            
            self.xdata_noisy=self.xdata+2*np.random.normal(size=self.xdata.shape)
            
            initial_guess_data=self.gaussian_estimator(self.x,self.xdata)
            error,popt = self.make_fit(self.gaussian_function, self.x, self.xdata_noisy,initial_guess=initial_guess_data)
            
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
            data = self.twoD_gaussian_function((self.x, self.y), 3, 100, 100, 20, 40, 10, 10)
            
            # add some noise to the data and try to fit the data generated beforehand
            
            self.data_noisy = data + 0.2*np.random.normal(size=data.shape)
            
            amplitude, xo, yo, sigma_x, sigma_y, theta, offset = self.twoD_gaussian_estimator(self.x,self.y,self.data_noisy)
            initial_guess_noisy = (amplitude, xo, yo, sigma_x, sigma_y, theta, offset)
            
            error,popt = self.make_fit(function=self.twoD_gaussian_function,axes=(self.x, self.y), data=self.data_noisy,initial_guess=initial_guess_noisy)
            
            data_fitted = self.twoD_gaussian_function((self.x, self.y), *popt)
            
            fig, ax = plt.subplots(1, 1)
            ax.hold(True)
            ax.imshow(self.data_noisy.reshape(201, 201), cmap=plt.cm.jet, origin='bottom',
                extent=(self.x.min(), self.x.max(), self.y.min(), self.y.max()))
            ax.contour(self.x, self.y, data_fitted.reshape(201, 201), 8, colors='w')
