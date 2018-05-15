# Setpoint interface        {#interface_setpoint}

## Description

This interface is used to manage a setpoint value.

### Example

This interface can be used to command the power, temperature or any value of a device that do not
provide on/off control or measured value.

## Detail


#### get_setpoint

Get the current setpoint

No parameter
Return a value in unit


#### set_setpoint

Set the current setpoint

Parameter : new value desired in unit 
Return the real new value

#### get_setpoint_unit

Return the unit that the setpoint value is set in as a tuple of ('abbreviation', 'full unit name')


#### get_setpoint_limits

Return limits within which the setpoint value can be set as a tuple of (low limit, high limit)
        
 