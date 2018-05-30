# Concept of pulse extraction methods {#pulse_extraction_methods}

## General description
The extraction methods take a 1D (for continuous counting) or 2D (for gated counting) integer array
representing the count trace as input together with method specific parameters. 
In case of gated counting, the first dimension of the count array is the gate index and the second 
dimension is the time bin index of the corresponding time trace.

Based on these inputs it will extract the actual laser-on part of the timetrace for each laser 
pulse.
So the returned object will be a 2D integer numpy array with the first dimension being the index of 
the laser pulse and the second dimension being the count trace of the corresponding laser pulse.

## Architecture
Each extraction method is a bound method of a child class of `PulseExtractorBase`. 
This base class provides read-only access to important attributes of `PulsedMeasurementLogic` via 
properties. (see ./logic/pulsed/pulse_extractor.py)
For the extraction you can therefore access all the information contained in 
`PulsedMeasurementLogic`, namely:
* `is_gated` (bool indicating if the fast counter is gated or not)
* `measurement_settings` (dict containing the parameters to define the current measurement)
* `sampling_information` (dict containing information about the discretization of the currently 
loaded waveform/sequence)
* `fast_counter_settings` (dict containing the current settings for the fast counter hardware)

If you need access to another attribute of the logic module simply add it as property to 
`PulseExtractorBase` but make sure to protect it properly against changes to the logic module.

In addition the base class provides access to the qudi logger which can be used just like in any 
other qudi module, e.g. `self.log.warning('I am a warning!')`

All parameters needed for the pulse extraction that can not be provided by the logic module need to 
be handed over to the extraction method directly as keyword arguments with default value.

When activating the `PulsedMeasurementLogic`, an instance of `PulseExtractor` will be created. 
This class finds and imports all child classes of `PulseExtractorBase` from the default directory 
./logic/pulsed/pulse_extraction_methods/. It will also inspect the extraction methods and create two 
dictionaries. One is holding references to the method itself and the other contains the keyword 
arguments together with the currently set values for each extraction method. In both cases the 
dictionary keys are the method names excluding the "analyse_" naming prefix.
Those two dictionaries can be accessed via properties of `PulseExtractor`.
The property holding the extraction parameters is masked in order to only return or set the 
parameter set for the currently selected extraction method.

## Method signature
Each extraction method must meet the following requirements:
* Is bound instance method of a `PulseExtractorBase` child class
* Method name starts with prefix `gated_` for extraction of gated counter timetraces or `ungated_` 
for extraction of continuous counter timetraces.
* First argument (after `self`) must be named `count_data`
* Additional parameters must be defined as optional keyword arguments
* Default values for additional arguments must be of type `int`, `float`, `str` or `bool`. 
Depending on the default argument type the GUI will automatically create the proper input widget.

## Adding new methods procedure
1. Define a class with `PulseExtractorBase` as the **ONLY** parent class.
2. Make sure the base class gets initialized with:
    ```python
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    ```
3. Define extraction methods in new class. (see section "Method signature")
4. Place the module containing your class definition in the default directory to import from 
(`./logic/pulsed/pulse_extraction_methods/`) or put it in a custom directory and specify the path in 
your config for the `PulsedMeasurementLogic` as ConfigOption "additional_extraction_path".

You can also simply add your extraction method to an already existing `PulseExtractorBase` child 
class. In that case you just need to follow step 3. 

By default _qudi_ ships with the default methods defined in 
`./logic/pulsed/pulse_extraction_methods/basic_extraction_methods.py`. This module should not be 
altered unless you intend to contribute your methods to the _qudi_ repository.

A template for a new `PulseExtractor` class could look like:
```python
class MyPulseExtractor(PulseExtractorBase):
    """ Description goes here """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def gated_my_method_name1(self, count_data, my_float_param=42.0, my_int_param=42):
        # Do something
        pass
        
    def ungated_my_method_name2(self, count_data, my_str_param='derp', my_bool_param=True):
        # Do something
        pass
    
    def _some_helper_method(self):
        pass
```
