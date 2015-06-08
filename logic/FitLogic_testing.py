# -*- coding: utf-8 -*-

import numpy as np
import scipy.optimize as opt
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel
from lmfit import Parameters
import scipy
import pylab as plt

#for filters:
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import scipy.optimize as op
import time

#TODO:
#Make Estimator, Fit method, comments, try smooth as estimator
class FitLogic():        
        """
        UNSTABLE:Jochen Scheuer
        This is the fitting class where fit models are defined and methods
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


            #redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters)                                     
            try:
                result=mod_final.fit(data, x=axis,params=params)
            except:
                self.logMsg('The 1D gaussian fit did not work.', \
                            msgType='message')
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
            """ This method performes a 2D gaussian fit on the provided data.
        
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
                           (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(x_axis[-1]-x_axis[0]),          None),
                           (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(y_axis[-1]-y_axis[0]) ,   None), 
                           (  'x_zero',    x_zero,      True,     (x_axis[0])-n_steps_x*stepsize_x ,         x_axis[-1]+n_steps_x*stepsize_x,               None),
                           (  'y_zero',     y_zero,     True,    (y_axis[0])-n_steps_y*stepsize_y ,         (y_axis[-1])+n_steps_y*stepsize_y,         None),
                           (  'theta',       0.,        True,           0. ,                             np.pi,               None),
                           (  'offset',      offset,    True,           0,                              1e7,                       None))
           

#           redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters) 

            try:
                result=mod.fit(data, x=axis,params=params)
            except:
                result=mod.fit(data, x=axis,params=params)
                self.logMsg('The 2D gaussian fit did not work:'+result.message, \
                                        msgType='message')
            
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

            #Additional routines for Lorentzian-like models

##############################################################################
############################################################################## 
        
        def find_offset_parameter(self,x_values=None,data=None):
            """ This method convolves the data with a lorentzian and the finds the
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
            
            if len(x_values)<50.:
                len_x=6
            if len(x_values)>=100.:
                len_x=10
            else:
                len_x=int(len(x_values)/10.)+1
                
            lorentz=mod.eval(x=np.linspace(0,len_x,len_x),amplitude=1,c=0.,sigma=len_x/4.,center=len_x/2.)
            data_smooth = filters.convolve1d(data, lorentz/lorentz.sum(),mode='constant',cval=data.max())   
            
            #finding most frequent value which is supposed to be the offset
            hist=np.histogram(data_smooth,bins=10)
            offset=(hist[1][hist[0].argmax()]+hist[1][hist[0].argmax()+1])/2.
            
            return data_smooth,offset

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
            
            data_smooth,offset=self.find_offset_parameter(x_axis,data)
            data_level=data-offset        
            data_min=data_level.min()       
            data_max=data_level.max()

            #estimate sigma
            numerical_integral=np.sum(data_level) * (x_axis[-1] - x_axis[0]) / len(x_axis)

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

#TODO: Add logmessage when value is changed            
            #redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters)                                     
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                result=model.fit(data, x=axis,params=params)
                self.logMsg('The 1D gaussian fit did not work. Error message:'+result.message, \
                            msgType='message')            
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
                    self.logMsg('Given parameter is no one dimensional array.', \
                                msgType='error')
                                
            
            #set paraameters 
            data_smooth,offset=self.find_offset_parameter(x_axis,data)            
            
            data_level=data_smooth-offset        

            #search for double lorentzian

            #first search for absolute minimum
            absolute_min=data_level.min()
            absolute_argmin=data_level.argmin()
            
            lorentz0_center=x_axis[absolute_argmin]
            lorentz0_amplitude=data.min()-offset
            
            #TODO: make threshold,minimal_threshold and sigma_threshold value a config variable
            
            #set thresholds            
            threshold=0.3*absolute_min
            minimal_threshold=0.01
            sigma_threshold_fraction=0.5
            sigma_threshold=sigma_threshold_fraction*absolute_min
            
#            search for the left end of the dip
            sigma_argleft=int(0)
            ii=0
            if absolute_argmin!=0:#if the minimum is at the end set this as boarder
                while True:
                    if absolute_argmin-ii<0: # if no minimum can be found decrease threshold
                        sigma_threshold*=0.9
                        ii=0
                    if abs(sigma_threshold)<abs(threshold): #if the dip is alsways over threshold the end is the 0 as set before
                        break
                    if sigma_argleft==0: #check if value was changed and search is finished
                        if abs(data_level[absolute_argmin-ii])<abs(sigma_threshold): # check if if value is lower as threshold this is the searched value
                            sigma_argleft=absolute_argmin-ii
    #                        print('here left', sigma_argleft,data_level[absolute_argmin-ii])
                    else: #if value is not zero the search was successful and finished
    #                    print('sigma left right',x_axis[sigma_argleft],data_level[sigma_argright],x_axis[sigma_argright],data_level[sigma_argright])
                        break
                    ii+=1

            #search for the right end of the dip
            sigma_threshold=sigma_threshold_fraction*absolute_min
            sigma_argright=int(0)                
            ii=0
            if absolute_argmin!=len(data)-1: #if the minimum is at the end set this as boarder
                while True:
                    if absolute_argmin+ii>len(data)-1: # if no minimum can be found decrease threshold
                        sigma_threshold*=0.9
                        ii=0
                    if abs(sigma_threshold)<abs(threshold):#if the dip is alsways over threshold the end is the most right index
                        sigma_argright=len(data)-1
                        break
                    if sigma_argright==0: #check if value was changed and search is finished
                        if abs(data_level[absolute_argmin+ii])<abs(sigma_threshold): # check if if value is lower as threshold this is the searched value
                                sigma_argright=absolute_argmin+ii 
                    else: #if value is not zero the search was successful and finished
                        break
                    ii+=1
            else: #in this case the value is the last index and should be search set as right argument
                sigma_argright=absolute_argmin

#           search for second lorentzian dip            
            left_index=int(0)
            right_index=len(x_axis)-1
                
            mid_index_left=sigma_argleft
            mid_index_right=sigma_argright

            if sigma_argleft==left_index: #if main first dip covers the whole left side search on the right side only
                lorentz1_center=x_axis[data_level[mid_index_right:right_index].argmin()+mid_index_right]
                lorentz1_amplitude=data_level[mid_index_right:right_index].min()
            elif sigma_argright==right_index:  #if main first dip covers the whole right side search on the left side only
                lorentz1_amplitude=data_level[left_index:mid_index_left].min()
                lorentz1_center=x_axis[data_level[left_index:mid_index_left].argmin()]
            else: # search for peak left and right of the dip
                while True: 
                    #set search area excluding the first dip
                    left_min=data_level[left_index:mid_index_left].min()
                    left_argmin=data_level[left_index:mid_index_left].argmin()
                    right_min=data_level[mid_index_right:right_index].min()
                    right_argmin=data_level[mid_index_right:right_index].argmin()
                    
                    if abs(left_min)>abs(threshold) and abs(left_min)>abs(right_min):
                        #there is a minimum on the left side which is higher than right side
                        lorentz1_amplitude=left_min
                        lorentz1_center=x_axis[left_argmin+left_index]
                        break
                    elif abs(right_min)>abs(threshold):
                        #there is a minimum on the right side which is higher than on left side
                        lorentz1_amplitude=right_min
                        lorentz1_center=x_axis[right_argmin+mid_index_right]
                        break
                    else: 
                        #no minimum at all over threshold so lowering threshold and resetting search area
                        threshold=threshold*3./4.
                        left_index=int(0)
                        right_index=len(x_axis)-1
                        mid_index_left=sigma_argleft
                        mid_index_right=sigma_argright
                        if abs(threshold/absolute_min)<abs(minimal_threshold): #if no second dip can be found set both to same value
                            self.logMsg('threshold to minimum ratio was too small to estimate two minima. So both are set to the same value', \
                                    msgType='message') 
                            error=-1
                            lorentz1_center=lorentz0_center
                            lorentz0_amplitude/=2.
                            lorentz1_amplitude=lorentz0_amplitude/2.
                            break
            
            #estimate sigma
            numerical_integral=np.sum(data_level) * (x_axis[-1] - x_axis[0]) / len(x_axis)

            lorentz0_sigma = abs(numerical_integral/2. / (np.pi * lorentz0_amplitude) )  
            lorentz1_sigma = abs( numerical_integral /2./ (np.pi * lorentz1_amplitude)  )

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
            
            #Defining standard parameters
            #            (Name,                  Value,          Vary,         Min,                    Max,                    Expr)
            params.add('lorentz0_amplitude',lorentz0_amplitude,  True,         None,                    -0.01,                    None)
            params.add(  'lorentz0_sigma',    lorentz0_sigma,    True,    (axis[1]-axis[0])/2 ,     (axis[-1]-axis[0])*4,   None)
            params.add(  'lorentz0_center',  lorentz0_center,    True,(axis[0])-n_steps*stepsize,(axis[-1])+n_steps*stepsize, None)
            params.add('lorentz1_amplitude',lorentz1_amplitude,  True,         None,                    -0.01,                    None)
            params.add(  'lorentz1_sigma',    lorentz1_sigma,    True,     (axis[1]-axis[0])/2 ,     (axis[-1]-axis[0])*4,   None)
            params.add(  'lorentz1_center',  lorentz1_center,    True,(axis[0])-n_steps*stepsize,(axis[-1])+n_steps*stepsize, None)
            params.add(    'c',                   offset,        True,        None,                    None,                  None)

            #redefine values of additional parameters
            if add_parameters!=None:  
                params=self.substitute_parameter(parameters=params,update_parameters=add_parameters)                                     
            try:
                result=model.fit(data, x=axis,params=params)
            except:
                result=model.fit(data, x=axis,params=params)
                self.logMsg('The double lorentuab fit did not work:'+result.message, \
                            msgType='message')
            
            return result


##############################################################################
##############################################################################

                        #N14 fitting

##############################################################################
##############################################################################  

        def estimate_N14(self,x_axis=None,data=None):
            """ This method provides an estimation of all fitting parameters for 
            fitting the three equdistant lorentzian dips of the hyperfine interaction
            of a N14 nuclear spin. Here the splitting is set as an expression, if the
            splitting is not exactly 2.15MHz the fit will not work.
        
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
            
            parameters.add('lorentz0_amplitude',value=data_smooth_lorentz.min()-offset,max=-1e-6)
            parameters.add('lorentz0_center',value=x_axis[data_smooth.argmin()]-2.15)
            parameters.add('lorentz0_sigma',value=0.5,min=0.01,max=4.)
            parameters.add('lorentz1_amplitude',value=parameters['lorentz0_amplitude'].value,max=-1e-6)
            parameters.add('lorentz1_center',value=parameters['lorentz0_center'].value+2.15,expr='lorentz0_center+2.15')
            parameters.add('lorentz1_sigma',value=parameters['lorentz0_sigma'].value,min=0.01,max=4.,expr='lorentz0_sigma')
            parameters.add('lorentz2_amplitude',value=parameters['lorentz0_amplitude'].value,max=-1e-6)
            parameters.add('lorentz2_center',value=parameters['lorentz1_center'].value+2.15,expr='lorentz0_center+4.3')
            parameters.add('lorentz2_sigma',value=parameters['lorentz0_sigma'].value,min=0.01,max=4.,expr='lorentz0_sigma')
            parameters.add('c',value=offset)
                        
            return parameters
            
            
        def make_N14_fit(self,axis=None,data=None,add_parameters=None):
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
                parameters=self.substitute_parameter(parameters=parameters,update_parameters=add_parameters)  

            mod,params = self.make_multiple_lorentzian_model(no_of_lor=3)
                                
            result=mod.fit(data=data,x=axis,params=parameters)


            return result

##############################################################################
##############################################################################

                        #N15 fitting

##############################################################################
##############################################################################  

        def estimate_N15(self,x_axis=None,data=None):
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
            
            
        def make_N15_fit(self,axis=None,data=None,add_parameters=None):
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
                parameters=self.substitute_parameter(parameters=parameters,update_parameters=add_parameters)  

            mod,params = self.make_multiple_lorentzian_model(no_of_lor=2)
                                
            result=mod.fit(data=data,x=axis,params=parameters)


            return result
            
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


            
        def double_lorentzian_testing(self):
            runs=np.linspace(0,1,1)
            results=np.array([runs,runs,runs,runs])
            for ii in runs:
                x = np.linspace(2850, 2900, 51)
                
                mod,params = self.make_multiple_lorentzian_model(no_of_lor=2)
    #            print('Parameters of the model',mod.param_names)
                
                p=Parameters()
                
#                center=np.random.random(1)*50+2805
    #            p.add('center',max=-1)
                p.add('lorentz0_amplitude',value=-abs(np.random.random(1)*50+100))
                p.add('lorentz0_center',value=np.random.random(1)*50.0+2850)
                p.add('lorentz0_sigma',value=abs(np.random.random(1)*2.+1.))
                p.add('lorentz1_amplitude',value=-abs(np.random.random(1)*50+100))
                p.add('lorentz1_center',value=np.random.random(1)*50.0+2850)
                p.add('lorentz1_sigma',value=abs(np.random.random(1)*2.+1.))
                p.add('c',value=100.)
                
#                print(p['lorentz0_center'].value,p['lorentz1_center'].value)
#                print('center left, right',p['lorentz0_center'].value,p['lorentz1_center'].value)
                data_noisy=(mod.eval(x=x,params=p) 
                                        + 2.*np.random.normal(size=x.shape))
                
                para=Parameters()
#                para.add('lorentz1_center',expr='lorentz0_center+20.0')
                error, lorentz0_amplitude,lorentz1_amplitude, lorentz0_center,lorentz1_center, lorentz0_sigma,lorentz1_sigma, offset = self.estimate_double_lorentz(x,data_noisy)

                print(lorentz0_center>lorentz1_center)
                result=self.make_double_lorentzian_fit(axis=x,data=data_noisy,add_parameters=para)
                print(result)
#                print('center 1 und 2',result.init_values['lorentz0_center'],result.init_values['lorentz1_center'])
                
#                print('center 1 und 2',result.best_values['lorentz0_center'],result.best_values['lorentz1_center'])
                #           gaussian filter            
                gaus=gaussian(10,10)
                data_smooth = filters.convolve1d(data_noisy, gaus/gaus.sum())
                       
#                print(result.fit_result())
                try:
    #            print(result.fit_report()
                    plt.plot(x,data_noisy)
                    plt.plot(x,result.init_fit,'-y')
                    plt.plot(x,result.best_fit,'-r')
                    plt.plot(x,data_smooth,'-g')
                except:
                    print('exception')
    ##            plt.plot(x_nice,mod.eval(x=x_nice,params=result.params),'-r')#
                plt.show()
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
            
test=FitLogic()
test.double_lorentzian_testing()   