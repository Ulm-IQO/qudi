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
            
        def make_fit(self,function=None,dimensions=None,data=None,initial_guess=None):
            # check parameter before using them (isinstance)
            # introduce details and only then return cov
            popt, pcov = opt.curve_fit(function,dimensions,data,initial_guess)
            return popt, pcov
        
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
            popt, pcov = self.make_fit(self.gaussian_function, self.x, self.xdata_noisy,initial_guess=initial_guess_data)
            
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
            
            popt, pcov = self.make_fit(function=self.twoD_gaussian_function,dimensions=(self.x, self.y), data=self.data_noisy,initial_guess=initial_guess_noisy)
            
            data_fitted = self.twoD_gaussian_function((self.x, self.y), *popt)
            
            fig, ax = plt.subplots(1, 1)
            ax.hold(True)
            ax.imshow(self.data_noisy.reshape(201, 201), cmap=plt.cm.jet, origin='bottom',
                extent=(self.x.min(), self.x.max(), self.y.min(), self.y.max()))
            ax.contour(self.x, self.y, data_fitted.reshape(201, 201), 8, colors='w')