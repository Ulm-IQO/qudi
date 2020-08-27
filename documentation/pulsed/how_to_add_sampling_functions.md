# Concept of sampling functions {#sampling_functions}

## General description
The basic analog waveform shapes (e.g. DC, sine, chirp etc.) to build a waveform from are provided 
by so called sampling functions. Those sampling functions are the atomic elements to build a 
waveform from. Each sampling function can be used to calculate analog voltages from a given array 
representing the discrete timing of arbitrary waveform generators.

For each sampling function properly included into qudi the PulseBlock editor in the GUI 
automatically includes the function together with its custom parameter set.

## Architecture
Each sampling function is a child class of `SamplingBase`. 
The base class provides methods to save and restore sampling function instances using _qudi_ 
StatusVars. It also provides the logging module to be used in the same way as in qudi modules. 
So you can call for example `self.log.error('My awesome error message!')` from your sampling 
function class.

Each `PulseBlockElement` instance created will contain as many sampling function instances as analog
channels active. During initialization the sampling function instance will receive a desired set of 
parameters needed for the respective function evaluation of the sampling function.
In case of the sampling function `Sin` this would be `amplitude`, `frequency` and `phase`.

In order to inspect this function specific parameter set, each sampling function class contains an 
attribute `params`. It is a dictionary with keys being the parameter names and values being 
dictionaries holding information about the parameter like default value, unit, domain of definition 
etc. All keys in the `params` dictionary are keyword arguments of the sampling function `__init__`.

The class `SamplingFunctions` has a classmethod `import_sampling_functions` which imports all child 
classes of `SamplingBase` as sampling functions and attaches the imported class names as callable to
the `SamplingFunctions` class. It also combines all `params` dictionaries into a single one called 
`parameters` where the keys are the sampling function names.

**WARNING:** _The class attributes of_ `SamplingFunctions` _can change during runtime. 
Do NOT keep references to class attributes in order to avoid a mismatch of definitions._

When activating the `SequenceGeneratorLogic`, `import_sampling_functions` will be called with the 
proper import paths. The default import path is ./logic/pulsed/sampling_function_defs/. 
An additional import path can be set using the `ConfigOption` `additional_sampling_functions_path`.

## Class signature
Each sampling function class must meet the following requirements:
* The parent class must be `SamplingBase` or another sampling function class
* `__init__` method must have all function parameters as optional keyword arguments.
* The class attribute `params` must be specified for all parameters 
(see `basic_sampling_functions.py` as example)
The attributes for each parameter are:
    * `'unit'` (The (SI) unit of the parameter)
    * `'init'` (The default value of the parameter)
    * `'min'` (The minimum allowed value of the parameter)
    * `'max'` (The maximum allowed value of the parameter)
    * `'type'` (The python type of the parameter. allowed types: `int`, `float`, `str`, `bool` and Enum subclass)
* If a parameter is not given in a call to `__init__`, it must be set using its default value 
defined in `params`
* Allowed parameter types are `int`, `float`, `str`, `bool` and subclasses of Enum (see example). 
Depending on the type the GUI will automatically create the proper input widget.
* Must implement a method `get_samples` which has only one argument `time_array`. This function will
calculate and return the analog voltages corresponding to the time bins provided by `time_array`.

## Adding new sampling functions procedure
1. Define a class with `SamplingBase` or another sampling function class as the parent class. The class name should be the 
function name.
2. Define all function parameters in `params` dictionary. (see section "Class signature")
3. Define `__init__` with all parameters as optional arguments. Upon creating an instance the 
parameters must be saved as instance variables. (use default values if necessary)
4. Implement `get_samples` to actually calculate the analog samples.
4. Place the module containing your class definitions in the default directory to import from 
(`./logic/pulsed/sampling_function_defs/`) or put it in a custom directory and specify the path
in your config for the `SequenceGeneratorLogic` as ConfigOption 
"additional_sampling_functions_path". **Notice:** You can either specify a single path as string or multiple paths as list of strings.

You can also simply add your new classes to an already existing module.

By default _qudi_ ships with the default sampling functions defined in 
`./logic/pulsed/sampling_function_defs/basic_sampling_functions.py`. This module should not be 
altered unless you intend to contribute your sampling functions to the _qudi_ repository.

A template for a new sampling function class could look like:
```python
from enum import Enum


class Colour(Enum):
    red = 1
    green = 2
    blue = 3


class MyFunc(SamplingBase):
    """ Description goes here """
    params = OrderedDict()
    params['my_float_param'] = {'unit': 'V', 'init': 0.0, 'min': 0.0, 'max': np.inf, 'type': float}
    params['my_int_param'] = {'unit': '', 'init': 0, 'min': 0, 'max': 42, 'type': int}
    params['my_enum_param'] = {'unit': '', 'init': Colour.green, 'min': Colour.red, 'max': Colour.blue, 'type': Colour}
    
    def __init__(self, my_float_param=None, my_int_param=None, my_enum_param=None):
        if my_float_param is None:
            self.my_float_param = params['my_float_param']['init']
        else:
            self.my_float_param = my_float_param
        if my_int_param is None:
            self.my_int_param = params['my_int_param']['init']
        else:
            self.my_int_param = my_int_param
        if my_enum_param is None:
            self.my_enum_param = params['my_enum_param']['init']
        else:
            self.my_enum_param = my_enum_param
        return

    def get_samples(self, time_array):
        # Calculate samples
        return np.zeros(time_array.size)
        
    def _some_helper_method(self):
        self.log.info('I am just some helper method and I have just been called.')
        pass
        

class MyFuncWithNewName(MyFunc):
    """ This is the same sampling function as MyFunc but it is now called MyFuncWithNewName """
    pass
```
