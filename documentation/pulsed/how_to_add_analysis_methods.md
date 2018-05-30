# Concept of pulse analysis methods {#pulse_analysis_methods}

## General description
The analysis methods take a 2D integer array of extracted laser pulses, i.e. the timetrace of just 
the laser-on-time without leading or trailing count data, as input together with method specific 
parameters. The first dimension of the laser array is the laser index and the second dimension is 
the time bin index of the corresponding time trace.

Based on these inputs it will calculate a certain numeric value for each laser pulse provided. 
So the returned object will be a 1D float numpy array of length `laser_data.shape[0]`.

## Architecture
Each analysis method is a bound method of a child class of `PulseAnalyzerBase`. 
This base class provides read-only access to important attributes of `PulsedMeasurementLogic` via 
properties. (see ./logic/pulsed/pulse_analyzer.py)
For the analysis you can therefore access all the information contained in `PulsedMeasurementLogic`, 
namely:
* `is_gated` (bool indicating if the fast counter is gated or not)
* `measurement_settings` (dict containing the parameters to define the current measurement)
* `sampling_information` (dict containing information about the discretization of the currently 
loaded waveform/sequence)
* `fast_counter_settings` (dict containing the current settings for the fast counter hardware)

If you need access to another attribute of the logic module simply add it as property to 
`PulseAnalyzerBase` but make sure to protect it properly against changes to the logic module.

In addition the base class provides access to the qudi logger which can be used just like in any 
other qudi module, e.g. `self.log.warning('I am a warning!')`

All parameters needed for the pulse analysis that can not be provided by the logic module need to be
handed over to the analysis method directly as keyword arguments with default value.

When activating the `PulsedMeasurementLogic`, an instance of `PulseAnalyzer` will be created. 
This class finds and imports all child classes of `PulseAnalyzerBase` from the default directory 
./logic/pulsed/pulsed_analysis_methods/. It will also inspect the analysis methods and create two 
dictionaries. One is holding references to the method itself and the other contains the keyword 
arguments together with the currently set values for each analysis method. In both cases the 
dictionary keys are the method names excluding the "analyse_" naming prefix.
Those two dictionaries can be accessed via properties of `PulseAnalyzer`.
The property holding the analysis parameters is masked in order to only return or set the parameter 
set for the currently selected analysis method.

## Method signature
Each analysis method must meet the following requirements:
* Is bound instance method of a `PulseAnalyzerBase` child class
* Method name starts with prefix `analyse_`
* First argument (after `self`) must be named `laser_data`
* Additional parameters must be defined as optional keyword arguments
* Default values for additional arguments must be of type `int`, `float`, `str` or `bool`. 
Depending on the default argument type the GUI will automatically create the proper input widget.

## Adding new methods procedure
1. Define a class with `PulseAnalyzerBase` as the **ONLY** parent class.
2. Make sure the base class gets initialized with:
    ```python
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    ```
3. Define analysis methods in new class. (see section "Method signature")
4. Place the module containing your class definition in the default directory to import from 
(`./logic/pulsed/pulsed_analysis_methods/`) or put it in a custom directory and specify the path in 
your config for the `PulsedMeasurementLogic` as ConfigOption "additional_analysis_path".

You can also simply add your analysis method to an already existing `PulseAnalyzerBase` child class. 
In that case you just need to follow step 3. 

By default _qudi_ ships with the default methods defined in 
`./logic/pulsed/pulsed_analysis_methods/basic_analysis_methods.py`. This module should not be 
altered unless you intend to contribute your methods to the _qudi_ repository.

A template for a new `PulseAnalyzer` class could look like:
```python
class MyPulseAnalyzer(PulseAnalyzerBase):
    """ Description goes here """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def analyse_my_method_name1(self, laser_data, my_float_param=42.0, my_int_param=42):
        # Do something
        pass
        
    def analyse_my_method_name2(self, laser_data, my_str_param='derp', my_bool_param=True):
        # Do something
        pass
        
    def _some_helper_method(self):
        pass
```
