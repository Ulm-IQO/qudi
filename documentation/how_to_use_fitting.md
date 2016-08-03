# How to use fitting in QuDi  {#fit_logic}

First of all it is important to mention that the naming convention
of methods is very important! Only if the methods are named right the
automated import works properly!

General procedure to create new fitting routines:

A fitting routine consists of three major parts:
1. a (mathematical) model `make_<custom>_model()`
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
    * The make_"<custom>"_model method returns, the model and a corresponding
     parameter dictionary
2. an estimator, which can extract initial values for
   the fitting routine from the passed data. `estimate_<custom>()`
    * Here values have to be estimated from the raw data
    * In many cases a clever convolution helps a lot
    * Offsets can be retrieved from find_offset_parameter method
    * All parameters are given via a Parameters object
    * The estimated values are returned inside a Parameters object
3. The actual fit method `make_<custom>_fit()`
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
have no extra underscores, and that it starts with `make_` and ends with `_fit`.
In order to distinguish between oneD and twoD models, every twoD model has to
include the string twoD e.g.

        def make_gaussian_fit() and def make_twoDgaussian_fit()

2. estimate function: `estimate_<custom>()` e.g. `estimate_gaussian()` if you only have one estimator, if
there are different estimators ``estimate_<custom>_<estimator name>``. it is important to have no extra
underscores, and that it starts with `estimate_`, e.g.

        def estimate_gaussian_dip() and def estimate_gaussian_peak()

2. model function: ``make_<custom>_model()``, if one wants to construct the
model from a custom (not built-in) function one can do that within the
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

# The model

Useful methods usable from the model are:

    model.eval(x=x_axis, parameters)

or

    linear_model.eval(x=np.linspace(0,10,100), slope=2., offset=10.)

One can retrieve the independent and variable variables from a model with:

     model.param_names and model.independent_vars

More information here: https://lmfit.github.io/lmfit-py/model.html

# The returned object of the fit method

In the object returned from the fit method many parameters are saved. Some useful values
are listed here:

*  a well readable fit_report `result.fit_report()`
*  an array of the fit corresponding to the x axis: ``result.best_fit``
*  an array of the initial parameters corresponding to the x axis: ``result.init_fit``
*  a parameters dictionary of the fitted values: ``result.best_values``
*  a parameters dictionary of the initial values: ``result.init_values``
*  information about the fit: ``result.message``
*  a boolean which tells if the fit worked: ``result.success``

More information at  https://lmfit.github.io/lmfit-py/model.html


# Parameters object

The parameter object can be created from a model:

        parameters = model.make_param()

It is also given back from the `make_<custom>_model()` method:

        model, parameters = make_<custom>_model()

Useful methods of the Parameters class are:
* add, e.g. parameters.add('frequency', value=1, vary=True, min=0, max=10,expr=None)
* add_many

                           #(Name,       Value,      Vary,           Min,                             Max,                       Expr)
        params.add_many(('amplitude',   amplitude,  True,        100,                               1e7,                           None),
                       (  'sigma_x',    sigma_x,    True,        1*(stepsize_x) ,              3*(x_axis[-1]-x_axis[0]),          None),
                       (  'sigma_y',  sigma_y,      True,   1*(stepsize_y) ,                        3*(y_axis[-1]-y_axis[0]) ,   None),
                       (  'x_zero',    x_zero,      True,     (x_axis[0])-n_steps_x*stepsize_x ,         x_axis[-1]+n_steps_x*stepsize_x,               None),
                       (  'y_zero',     y_zero,     True,    (y_axis[0])-n_steps_y*stepsize_y ,         (y_axis[-1])+n_steps_y*stepsize_y,         None),
                       (  'theta',       0.,        True,           0. ,                             np.pi,               None),
                       (  'offset',      offset,    True,           0,                              1e7,                       None))

Single changes can be set in the following way:

        params['amplitude'].min = 0.0
        params['amplitude'].max = 10.0
        params['lorentz1'].expr='lorentz0_center+2.15'
        params['amplitude'].vary = True
        params['amplitude'].value = 0.12

See very detailed description: https://lmfit.github.io/lmfit-py/parameters.html


# General functions

*  Searching a double dip in data:

       _search_double_dip()

*  Search the end of a dip. This can be used to exclude a dip from data in order to find
second dip, or one can estimate with this method the width of a dip/peak

        _search_end_of_dip()

*  Find offset from peaklike data, here first a lorentzian filter is applied on the data
and the a histogram is made. The most frequent value is supposed to be the offset value:

        find_offset_parameter()

* Smooth data with a gaussian filter, the filter is adjusted in size depending on
the length of the input data:

        gaussian_smoothing()

# List of fit functions

This list can be read out in the manager console:

        fitlogic.oneD_fit_methods and fitlogic.twoD_fit_methods