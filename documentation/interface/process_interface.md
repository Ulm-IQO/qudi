# Process interface        {#interface_process}

## Description

This interface is used to manage a process value or in another words a measure value of a simple sensor

### Example

This interface can be used to measure the power, temperature or any value of a device



#### get_process_value

Return a measured value

No parameter
Return a value in unit


#### get_process_unit

Return the unit that the value is measured in as a tuple of ('abbreviation', 'full unit name')

No parameter
Return tuple of ('abbreviation', 'full unit name')
