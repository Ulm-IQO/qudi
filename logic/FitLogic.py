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
            self.testing()
            
        def make_fit(self):
            pass
        
        def twoD_gaussian_function(self,xdata_tuple,amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
            (x, y) = xdata_tuple
            xo = float(xo)
            yo = float(yo)    
            a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)
            b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)
            c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)
            g = offset + amplitude*np.exp( - (a*((x-xo)**2) + 2*b*(x-xo)*(y-yo) 
                                    + c*((y-yo)**2)))
            return g.ravel()
            
        def twoD_gaussian_estimator():
            pass
            
        def gaussian_function(xdata,amplitude, x0, sigma):
            gaussian=amplitude*np.exp(-(xdata-x0)**2/(2*sigma**2))
            return gaussian
        
        def gaussian_estimator():
            pass
        
        def testing(self):    
            # Create x and y indices
            x = np.linspace(0, 200, 201)
            y = np.linspace(0, 200, 201)
            x, y = np.meshgrid(x, y)
            
            #create data
            data = self.twoD_gaussian_function((x, y), 3, 100, 100, 20, 40, 10, 10)
            
            # plot twoD_Gaussian data generated above
            plt.figure()
            plt.imshow(data.reshape(201, 201),origin='bottom')
            plt.colorbar()
            
            # add some noise to the data and try to fit the data generated beforehand
            initial_guess = (3,100,100,20,40,0,10)
            
            data_noisy = data + 0.2*np.random.normal(size=data.shape)
            
            popt, pcov = opt.curve_fit(self.twoD_gaussian_function,(x, y), data_noisy,p0=initial_guess)
            
            data_fitted = self.twoD_gaussian_function((x, y), *popt)
            
            fig, ax = plt.subplots(1, 1)
            ax.hold(True)
            ax.imshow(data_noisy.reshape(201, 201), cmap=plt.cm.jet, origin='bottom',
                extent=(x.min(), x.max(), y.min(), y.max()))
            ax.contour(x, y, data_fitted.reshape(201, 201), 8, colors='w')

        
#    #testing 1D gaussian
#         
#        x = np.linspace(0, 200, 201)
#        
#        xdata=gaussian_function(x,10,80,20)
#        
#        xdata_noisy=xdata+2*np.random.normal(size=xdata.shape)
#        
#        plt.figure()
#        plt.plot(xdata)
#        plt.plot(xdata_noisy)
#        plt.show()
#        
#        popt, pcov = opt.curve_fit(gaussian_function, x, xdata_noisy,p0=[10,80,20])
#        
#        plt.figure()
#        plt.plot(x,gaussian_function(x, *popt))
#        plt.plot(xdata_noisy)
#        plt.show()
#        
#        #estimate mean and standard deviation
#        mean = np.mean(x * xdata_noisy)
#        sigma = sum(xdata * (x - mean)**2)
#        print('mean, sigma',mean, sigma)
#        #do the fit!
#        popt, pcov = opt.curve_fit(gaussian_function, x, xdata_noisy, p0 = [10, mean, sigma])
#        #plot the fit results
#        plt.figure()
#        plt.plot(x,gaussian_function(xdata, *popt))
#        #confront with the given data
#        plt.plot(x,xdata,'ok')
