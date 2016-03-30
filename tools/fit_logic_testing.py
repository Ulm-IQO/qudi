# -*- coding: utf-8 -*-

import numpy as np
import scipy.optimize as opt
from scipy.interpolate import InterpolatedUnivariateSpline
from lmfit.models import Model,ConstantModel,LorentzianModel,GaussianModel,LinearModel
from lmfit import Parameters
import scipy
import matplotlib.pylab as plt
from scipy.signal import wiener, filtfilt, butter, gaussian, freqz
from scipy.ndimage import filters
import time
import random
import importlib
from os import listdir,getcwd
from os.path import isfile, join 
import os
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
        def __init__(self):
            
            filenames=[]
#            
#            for path in directories:
            path=join( getcwd()[:-5],'logic','fitmethods')
            for f in listdir(path):
                if isfile(join(path,f)):
                    filenames.append(f[:-3])
            current_path= getcwd()
            os.chdir(path)
            for files in filenames:
                
                mod = importlib.import_module('{}'.format(files))
                for method in dir(mod):
                    try:
                        if callable(getattr(mod,method)):
                            setattr(FitLogic,method,getattr(mod,method)) 
#                            print(method)
                    except:
                        self.logMsg('It was not possible to import element {} into FitLogic.'.format(method),
                                msgType='error')
                                
            os.chdir(current_path)




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
            gmod,params = self.make_twoD_gaussian_model()
            
            data= gmod.eval(x=axes,amplitude=amplitude,x_zero=x_zero,y_zero=y_zero,sigma_x=sigma_x,sigma_y=sigma_y,theta=theta_here, offset=offset)
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
            plt.show()
        
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
                self._search_double_dip(x, data_level,make_prints=False)

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
test.oneD_testing()
test.twoD_testing()
#test.lorentzian_testing()
#test.double_gaussian_testing()
#test.double_lorentzian_testing()
#test.powerfluorescence_testing()
