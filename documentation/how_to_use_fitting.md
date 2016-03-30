# How to use fitting in QuDi  {#fit_logic}

First of all it is important to mention that the naming convention
of methods is very important! Only if the methods are named right the
automatic import works properly!

General procedure to create new fitting routines:

A fitting routine consists out of three major parts:
1. a (mathematical) Model you have for the passed data
    *  Here we use the lmfit package, which has a couple of standard
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

# Naming convention:

1. fit method: `make_<custom>_fit()` it is important to
have no extra underscores, and that it starts with `make_` and ends with `_fit`, e.g.

        def make_gaussian_fit()

2. estimate function: `estimate_<custom>()` e.g. `estimate_gaussian()` if you only have one estimator, if
there are different estimators ``estimate_<custom>_<estimator name>``. it is important to have no extra
underscores, and that it starts with `estimate_`, e.g.

        def estimate_gaussian_dip() and def estimate_gaussian_peak()

2. model function: ``make_<custom>_model()``, if one want to make construct the
model from a custom (not built-in) funciton one can do that within the
 `make_<custom>_model()`` method e.g.

            def make_sine_model(self):
                """ This method creates a model of sine.

                @return tuple: (object model, object params)
                """
                def sine_function(x, amplitude, frequency,phase):
                    """
                    Function of a sine.
                    @param x: variable variable - e.g. time
                    @param amplitude: amplitude
                    @param frequency: frequency
                    @param phase: phase

                    @return: sine function: in order to use it as a model
                    """

                    return amplitude*np.sin(2*np.pi*frequency*x+phase)

                model = Model(sine_function, prefix='s0')

                params = model.make_params()

                return model, params