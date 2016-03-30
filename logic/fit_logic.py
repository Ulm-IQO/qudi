# -*- coding: utf-8 -*-
# unstable: Jochen Scheuer

from logic.generic_logic import GenericLogic
from core.util.mutex import Mutex

import importlib

from os import listdir, getcwd
from os.path import isfile, join

# FIXME: In general is it needed for any purposes to use weighting?
# FIXME: Don't understand exactly when you return error code...

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
              substitute_parameter method
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
    # declare connectors
    _out = {'fitlogic': 'FitLogic'}

    def __init__(self, manager, name, config, **kwargs):
        # declare actions for state transitions
        state_actions = {'onactivate': self.activation,
                         'ondeactivate': self.deactivation}
        GenericLogic.__init__(self, manager, name, config, state_actions,
                              **kwargs)
        # locking for thread safety
        self.lock = Mutex()

        filenames = []
#       for path in directories:
        path = join(getcwd(), 'logic', 'fitmethods')
        for f in listdir(path):
            if isfile(join(path,f)):
                filenames.append(f[:-3])
        #print(filenames)
        for files in filenames:
            mod = importlib.import_module('logic.fitmethods.{}'.format(files))
            for method in dir(mod):
                try:
                    if callable(getattr(mod, method)):
                        setattr(FitLogic, method, getattr(mod, method))
                        self.logMsg('The {} method was addad into FitLogic.'.format(method),
                            msgType='message')
                #print(method)
                except:
                    self.logMsg('It was not possible to import element {} into FitLogic.'.format(method),
                            msgType='error')


    def activation(self, e):
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

    def deactivation(self, e):
        pass
