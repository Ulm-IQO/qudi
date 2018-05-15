# camera interface     {#interface_steppers}    

## Description

This interface is used to manage and visualize a simple camera


### Detail


#### get_name

Get a name to identify the camera within the GUI

Return (string) name

#### get_size

Retrieve size of the image

Return  an integer tuple : (width, height)


#### support_live_acquisition

Return whether or not the camera can take care of live acquisition. If not, the logic should take care
of this feature

Return bool


####  start_live_acquisition

Start a continuous acquisition

Return (boolean) Success ?

#### start_single_acquisition
 
Start a single acquisition

Return (boolean) Success ?

#### stop_acquisition

Stop/abort live or single acquisition

Return (boolean) Success ?

#### get_acquired_data

Return an array of last acquired image in format [[row],[row]...]


#### set_exposure

Set the exposure time in seconds

Return (float) new exposure time


#### get_exposure

Get the exposure time in seconds

Return (float) exposure time

#### set_gain

Set the gain

Return (float) new exposure gain

#### get_gain

Get the gain

Return (float) exposure gain

   
#### get_ready_state

Is the camera ready for an acquisition ?

Return: (bool) ready ?

