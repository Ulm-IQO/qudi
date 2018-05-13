# Setpoint controller interface        {#interface_process_controller}

## Description

This interface is used to manage a controller with a setpoint value.

This interface use two sub-interfaces :
- ProcessInterface : An interface to read a process value
- SetpointInterface : An interface to control a setpoint value

To this two sub interfaces, this one add 'enable state' feature.

### Example

This interface can be used to monitor and control, for example, the temperature, power, pressure of an instrument that require a setpoint value.

## Detail


#### get_enabled

Get the current state of the controller

No parameter
Return a boolean (true if enabled, false if not)


#### set_enabled

Set the current state of the controller

Parameter : Boolean ()
Return the new value 



