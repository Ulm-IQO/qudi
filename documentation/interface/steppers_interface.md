# Steppers interface     {#interface_steppers}    

## Description

This interface is used to manage multiples axis piezo steppers.
This interface is not for doing scans. It is a wrapper around general piezo steppers features
to control them "by hand". 
It can be useful for debugging or prototyping and also to provide tools for semi automatic calibration

### Example

Piezo steppers are a useful device to access different zone of a sample over long distances.
If you have a controller, you can use this interface to interact with it.

### Convention

##### Getters and setters 

This interface implement getters and setters as only one overloaded function.
For these function, if a value is provided, it is set as new value.
In every case, the last value is returned

##### Buffered value

Sometime you want to get the last read value of a parameter for a non critical fast application.
In this case, you can pass the _buffered_ = True option so that the hardware module respond right away. 

### Detail


#### axis

Get a tuple of all \<axis identifier\>

The axis identifier might be an integer or a string

#### voltage_range

Get the voltage range of an axis

Parameter : \<axis\>

Return the voltage range in Volt as a tuple (min, max)


#### frequency_range

Get the frequency range of an axis

Parameter : \<axis\>

Return the frequency range in Hertz as a tuple (min, max)

#### position_range

Get the position range of an axis

Parameter : \<axis\>

Return the range in µm as a tuple (min, max)

#### capacitance

Get the capacitance of an axis

Parameter : \<axis\>, buffered (optional)

Return the capacitance in Farad 

#### voltage

Get the voltage of an axis

Parameter : \<axis\>, buffered (optional)

Return the voltage in Volt 

#### frequency

Get the frequency of an axis

Parameter : \<axis\>, buffered (optional)

Return the frequency in Hertz 

#### steps

Execute n steps (positive or negative) on a given axis in current config

Parameter : \<axis\>, number, buffered (optional)

#### stop

Stop movement on all or a given axis

Parameter : \<axis\> (optional)
