# Concept of predefined generate methods {#predefined_generate_methods}

## General description
We call predefined generate methods a method that programmatically arranges `PulseBlockElement` 
instances in order to generate a `PulseBlockEnsemble` or `PulseSequence` instance without using the 
(graphical) pulse editors. In addition these methods also define the actual pulsed measurement they 
are designed for by adding all necessary measurement parameters to the created object instance dict 
attribute `measurement_information`.

For each predefined method properly included into qudi the GUI can automatically create an easy 
interface to create a pulsed measurement sequence with a custom parameter set.

## Architecture
Each generate method is a bound method of a child class of `PredefinedGeneratorBase`. 
This base class provides read-only access to important attributes of `SequenceGeneratorLogic` via 
properties. (see ./logic/pulsed/pulse_objects.py)
For the generation you can therefore access all the information contained in 
`SequenceGeneratorLogic`, namely:
* `pulse_generator_settings` (dict containing the current settings for the pulse generator hardware)
* `generation_parameters` (dict containing commonly used generation parameters, e.g. rabi_period, 
laser_channel etc.)
* `channel_set` (set of currently active analog and digital channels)
* `analog_channels` (set of currently active analog channels)
* `digital_channels` (set of currently active digital channels)
* `laser_channel` (string descriptor of the currently selected laser trigger channel)
* `sync_channel` (string descriptor of the currently selected counter sync trigger channel)
* `gate_channel` (string descriptor of the currently selected counter gate trigger channel)
* `analog_trigger_voltage` (logical high voltage in case an analog channel is used as trigger)
* `laser_delay` (the delay in seconds between the laser trigger and the actual laser exposure)
* `microwave_channel` (the pulse generator channel used for microwave generation)
* `microwave_frequency` (the microwave frequency to be used)
* `microwave_amplitude` (the microwave amplitude to be used)
* `laser_length` (dict containing the current settings for the fast counter hardware)
* `wait_time` (the wait time after a laser pulse before any microwave irradiation takes place)
* `rabi_period` (the rabi period of the spin to manipulate in seconds)

If you need access to another attribute of the logic module simply add it as property to 
`PredefinedGeneratorBase` but make sure to protect it properly against changes to the logic module.

The base class also provides commonly used helper methods to reduce code duplication in the actual 
generate methods. If you think a helper method of general interest is missing feel free to add it to
the base class.

In addition the base class provides access to the qudi logger which can be used just like in any 
other qudi module, e.g. `self.log.warning('I am a warning!')`

All parameters needed for the generation that can not be provided by the logic module need to be
handed over to the generation method directly as keyword arguments with default value.

When activating the `SequenceGeneratorLogic`, an instance of `PulseObjectGenerator` will be created. 
This class finds and imports all child classes of `PredefinedGeneratorBase` from the default 
directory ./logic/pulsed/predefined_generate_methods/. It will also inspect the generate methods and
create two dictionaries. One is holding references to the method itself and the other contains the 
keyword arguments together with the currently set values for each generation method. In both cases 
the dictionary keys are the method names excluding the "generate_" naming prefix.
Those two dictionaries can be accessed via properties of `PulseObjectGenerator`.
The property holding the generation parameters is masked in order to only return or set the 
parameter set for the currently selected generation method.

## Method signature
Each generation method must meet the following requirements:
* Is bound instance method of a `PredefinedGeneratorBase` child class
* Method name starts with prefix `generate_`
* Must contain the optional keyword argument `name` to give the instance to created a name
* Additional parameters must be defined as optional keyword arguments
* Default values for additional arguments must be of type `int`, `float`, `str` or `bool`. 
Depending on the default argument type the GUI will automatically create the proper input widget.

## Adding new methods procedure
1. Define a class with `PredefinedGeneratorBase` as the **ONLY** parent class.
2. Make sure the base class gets initialized with:
    ```python
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    ```
3. Define generate methods in new class. (see section "Method signature")
4. Place the module containing your class definition in the default directory to import from 
(`./logic/pulsed/predefined_generate_methods/`) or put it in a custom directory and specify the path
in your config for the `SequenceGeneratorLogic` as ConfigOption 
"additional_predefined_methods_path".

You can also simply add your analysis method to an already existing `PredefinedGeneratorBase` child 
class. In that case you just need to follow step 3. 

By default _qudi_ ships with the default methods defined in 
`./logic/pulsed/predefined_generate_methods/basic_predefined_methods.py`. This module should not be 
altered unless you intend to contribute your methods to the _qudi_ repository.

A template for a new `PredefinedGenerator` class could look like:
```python
class MyPredefinedGeneratorBase(PredefinedGeneratorBase):
    """ Description goes here """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_my_method_name1(self, name='my_name', my_float_param=42.0, my_int_param=42):
        # Do something
        pass
        
    def generate_my_method_name2(self, name='my_name', my_str_param='derp', my_bool_param=True):
        # Do something
        pass
        
    def _some_helper_method(self):
        pass
```
