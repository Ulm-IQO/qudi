# Joystick controller {#how_to_joystick}

Qudi support the use of a controller to interact with some modules.

The list of currently implemented modules is :
* Scanner
* Optimizer
* POI manager

The list of currently supported controller is :
* Xbox controller (through windows xinput api)

See the "tutorial_test_joystick.cfg" for haw to get started. It will work by default with
the Xbox controller.

## Usage

The controller can be plugged/unplugged after Qudi module is started without issues.

For a module to listen to the inputs, some "trigger" configuration must be active.
For example the scanner logic by default listen only if the right side Up button is pushed (Y on xbox controller).
This feature a bit cumbersome protects user from accidental usage and give the possiblity to use multiple modules
easily.

### Scanner inputs

Default trigger key : Right side up

Left side buttons : move my the cursor by the amount ``button_step_ratio x total_range``
Trigger buttons ("shoulder") : move the cursor the same in Z
Left side joystick : move continuously in X/Y
Trigger joysticks : move continuously in z (left negative, up positive)

### Optimizer inputs

Default trigger key : Right side right

Both shoulder : Optimize

### POI inputs

Default trigger key : Right side down

Both shoulder : Refocus current POI


## How to add new modules

To add a new module, one need to create a new connector on qudi/loglc/logic_connectors
Looking at how the exiting one are done is a good way to start.

The idea is that a module register to the JoystickLogic and specify some trigger keys.
 Whenever the controller state matches the trigger keys, a callback function is called with the raw state and 
 some precomputed parameters. (ex: right_trigger - left_trigger)
 
## Error correction

As every physical input, the joystick have some error. To prevent them from having to much impact, the useal method is 
use a threshold value. If the joystick is moved less that 5% for example, this counts as zero.
This method sometime is not enough if the controller have rest position far from zero.
The method activate by default by the ``compensate_error`` config option is to measure the mean value of each axis and
simply subtract it to the raw state before applying the threshold.

This is done internally in the JoystickLogic, the connector directly get the corrected values.

### Gamma correction

Having a response linear with the joystick displacement is not always ideal. Some modules like
joystick_to_confocal have ``joystick_gamma_correction`` config (gamma = 2.0 by default) that apply a power to the 
normalized displacement. 