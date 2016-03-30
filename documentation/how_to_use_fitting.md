# How to use fitting in QuDi  {#fit_logic}

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
