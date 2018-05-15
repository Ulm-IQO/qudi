# Process control interface        {#interface_process_control}

## Description

This interface is used to manage a control value.

### Example

This interface can be used to command the power, flow or any value of a device that can be turned on or off.

## Detail


#### set_control_value

Set the value of the controlled process variable

#### get_control_value

Get the value of the controlled process variable

#### get_control_unit

Return the unit that the value is set in as a tuple of ('abreviation', 'full unit name')


#### get_control_limits

Return limits within which the controlled value can be set as a tuple of (low limit, high limit)
        
#### get_enabled

Return the enabled state of the control device  

#### set_enabled

Set the enabled state of the control device 
        
